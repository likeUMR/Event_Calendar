# coding=utf-8

import argparse
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from openai import BadRequestError, OpenAI


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_DIR = ROOT / "数据" / "活动信息_人工"
DEFAULT_BASE_URL = "https://relay.tuyoo.com/v1"
DEFAULT_MODEL = "gemini-3-flash-preview"
DEFAULT_API_KEY = "9sQQXa693LiYsiNU7f9aCfA63fDe4d56819e8bB5D814A35e"

CATEGORY_LABELS = {
    1: "和本游戏完全无关",
    2: "无法确定是否和本游戏无关",
    3: "和本游戏有关，但无法确定和本活动有关",
    4: "和本活动有关，且是封面图、宣传图等无实际玩法界面的图片",
    5: "和本活动有关，且是活动内截图等展现了实际玩法界面的图片",
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="用多模态大模型筛选活动信息 JSON 中每个活动类型的图片。"
    )
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR, help="人工活动 JSON 目录")
    parser.add_argument("--file", type=Path, help="只处理指定 JSON 文件")
    parser.add_argument("--rank", type=int, nargs="*", help="只处理指定 rank，例如 --rank 1 3 5")
    parser.add_argument("--activity-type", help="只处理指定 activity_types[].type")
    parser.add_argument("--limit-activities", type=int, help="最多处理多少个有图片的活动类型")
    parser.add_argument("--max-images-per-activity", type=int, help="每个活动最多传入多少张图片")
    parser.add_argument("--write", action="store_true", help="把分类结果写回 JSON；默认只打印预览")
    parser.add_argument("--force", action="store_true", help="已分类的图片也重新请求模型")
    parser.add_argument("--workers", type=int, default=1, help="并行处理活动的 worker 数；默认 1")
    parser.add_argument("--base-url", default=os.getenv("LLM_BASE_URL", DEFAULT_BASE_URL), help="LLM API base_url")
    parser.add_argument("--model", default=os.getenv("LLM_MODEL", DEFAULT_MODEL), help="模型名")
    parser.add_argument(
        "--api-key",
        default=os.getenv("LLM_TOKEN") or os.getenv("OPENAI_API_KEY") or DEFAULT_API_KEY,
        help="API key；也可用环境变量 LLM_TOKEN 或 OPENAI_API_KEY",
    )
    return parser.parse_args()


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def iter_json_files(args):
    if args.file:
        yield args.file
        return
    rank_set = set(args.rank or [])
    for path in sorted(args.input_dir.glob("*.json")):
        if not rank_set:
            yield path
            continue
        try:
            payload = load_json(path)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"[skip] {path.name}: JSON 读取失败: {exc}", file=sys.stderr)
            continue
        if int(payload.get("rank", -1)) in rank_set:
            yield path


def image_already_classified(image):
    result = image.get("llm_image_filter")
    return isinstance(result, dict) and result.get("category") in CATEGORY_LABELS


def activity_images(activity, force, max_images):
    images = activity.get("images") or []
    selected = []
    for image in images:
        if not isinstance(image, dict) or not image.get("url"):
            continue
        if not force and image_already_classified(image):
            continue
        selected.append(image)
        if max_images and len(selected) >= max_images:
            break
    return selected


def build_prompt(payload, activity, images):
    image_rows = []
    for index, image in enumerate(images, start=1):
        image_rows.append({"image_index": index})

    context = {
        "game_name": payload.get("name"),
        "game_rank": payload.get("rank"),
        "activity_type": activity.get("type"),
        "activity_display_name": activity.get("display_name"),
        "activity_description": activity.get("description"),
        "activity_examples": activity.get("examples") or [],
        "activity_market_research_notes": activity.get("market_research_notes") or "",
        "images": image_rows,
    }
    return (
        "你是手游竞品活动图片审核助手。请根据给定游戏、活动信息和每张图片内容，对图片逐张分类。\n\n"
        "分类只能使用以下数字：\n"
        "1. 和本游戏完全无关\n"
        "2. 无法确定是否和本游戏无关\n"
        "3. 和本游戏有关，但无法确定和本活动有关\n"
        "4. 和本活动有关，且是封面图、宣传图等无实际玩法界面的图片\n"
        "5. 和本活动有关，且是活动内截图等展现了实际玩法界面的图片\n\n"
        "判定要求：\n"
        "- 本游戏指 game_name；本活动指 activity_display_name / activity_type / description / examples 描述的活动类型。\n"
        "- 如果图片只是该游戏 App 图标、角色头像、商店封面、商店截图、通用品牌图、通用宣传图，选 3。\n"
        "- 如果图片能确认属于本活动，但主要是活动标题图、活动 banner、封面、宣传海报、加载图、活动介绍图，且没有实际可操作玩法界面，选 4。\n"
        "- 只有图片能确认属于本活动，并展示活动内实际玩法界面，才选 5；例如活动地图、活动棋盘、活动任务列表、活动奖励轨、活动进度条、活动排行榜、活动关卡、活动内消耗/收集资源界面。\n"
        "- 看不清、证据不足、图片内容和活动描述只是弱相关时，保守选择 2 或 3。\n"
        "- 必须覆盖输入的每一个 image_index。\n\n"
        "只输出 JSON，不要 Markdown，不要解释性前后缀。格式如下：\n"
        "{\n"
        '  "images": [\n'
        '    {"image_index": 1, "category": 4, "confidence": 0.86, "reason": "简短中文理由"}\n'
        "  ]\n"
        "}\n\n"
        "待分类数据：\n"
        f"{json.dumps(context, ensure_ascii=False, indent=2)}"
    )


def build_messages(payload, activity, images):
    content = [{"type": "text", "text": build_prompt(payload, activity, images)}]
    for index, image in enumerate(images, start=1):
        content.append({"type": "text", "text": f"image_index={index}"})
        content.append({"type": "image_url", "image_url": {"url": image["url"]}})
    return [
        {"role": "system", "content": "You classify mobile game event images and return strict JSON."},
        {"role": "user", "content": content},
    ]


def extract_json(text):
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.S)
        if not match:
            raise
        return json.loads(match.group(0))


def normalize_result(raw_result, image_count):
    payload = raw_result if isinstance(raw_result, dict) else {}
    items = payload.get("images")
    if not isinstance(items, list):
        raise ValueError("模型返回 JSON 中缺少 images 数组")

    by_index = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        try:
            image_index = int(item.get("image_index"))
            category = int(item.get("category"))
        except (TypeError, ValueError):
            continue
        if image_index < 1 or image_index > image_count or category not in CATEGORY_LABELS:
            continue
        confidence = item.get("confidence")
        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            confidence = None
        by_index[image_index] = {
            "category": category,
            "category_label": CATEGORY_LABELS[category],
            "confidence": confidence,
            "reason": str(item.get("reason") or "").strip(),
        }

    missing = [index for index in range(1, image_count + 1) if index not in by_index]
    if missing:
        raise ValueError(f"模型返回缺少 image_index: {missing}")
    return by_index


def classify_activity(client, model, payload, activity, images):
    try:
        response = client.chat.completions.create(
            model=model,
            messages=build_messages(payload, activity, images),
        )
        text = response.choices[0].message.content
        raw_result = extract_json(text)
        return normalize_result(raw_result, len(images)), text
    except BadRequestError as exc:
        if len(images) == 1:
            return {
                1: {
                    "category": 2,
                    "category_label": CATEGORY_LABELS[2],
                    "confidence": 0.0,
                    "reason": f"模型接口无法读取或接受该图片 URL，已按无法确定处理：{exc}",
                }
            }, str(exc)

        print(
            f"[warn] batch request failed for {activity.get('type')}; "
            "retrying images one by one.",
            file=sys.stderr,
        )
        merged = {}
        raw_texts = []
        for original_index, image in enumerate(images, start=1):
            single_results, single_text = classify_activity(client, model, payload, activity, [image])
            merged[original_index] = single_results[1]
            raw_texts.append(f"image_index={original_index}: {single_text}")
        return merged, "\n".join(raw_texts)


def apply_results(images, results, model):
    classified_at = datetime.now(timezone.utc).isoformat()
    for index, image in enumerate(images, start=1):
        image["llm_image_filter"] = {
            **results[index],
            "model": model,
            "classified_at": classified_at,
        }


def print_results(path, payload, activity, images, results, raw_text):
    print(f"\n[file] {path.name}")
    print(f"[game] {payload.get('name')}")
    print(f"[activity] {activity.get('type')} / {activity.get('display_name')}")
    for index, image in enumerate(images, start=1):
        result = results[index]
        print(
            f"  [{index}] category={result['category']} "
            f"({result['category_label']}), confidence={result['confidence']}, "
            f"reason={result['reason']}"
        )
        print(f"      url={image.get('url')}")
    if not results and raw_text:
        print(raw_text)


def classify_activity_job(api_key, base_url, model, path, payload, activity, images):
    client = OpenAI(api_key=api_key, base_url=base_url)
    results, raw_text = classify_activity(client, model, payload, activity, images)
    return path, payload, activity, images, results, raw_text


def mark_filter_meta(payload, model):
    payload["manual_image_filter"] = {
        "method": "llm_multimodal_image_classification",
        "model": model,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "category_labels": CATEGORY_LABELS,
    }


def main():
    args = parse_args()
    if not args.api_key:
        raise SystemExit("缺少 API key，请设置 LLM_TOKEN 或使用 --api-key。")

    workers = max(1, args.workers)
    client = OpenAI(api_key=args.api_key, base_url=args.base_url)
    processed = 0
    changed_files = 0

    for path in iter_json_files(args):
        payload = load_json(path)
        file_changed = False
        jobs = []
        for activity in payload.get("activity_types") or []:
            if not isinstance(activity, dict):
                continue
            if args.activity_type and activity.get("type") != args.activity_type:
                continue
            images = activity_images(activity, args.force, args.max_images_per_activity)
            if not images:
                continue
            if args.limit_activities and processed >= args.limit_activities:
                break

            jobs.append((activity, images))
            processed += 1

        if not jobs:
            continue

        if workers == 1:
            for activity, images in jobs:
                print(f"[request] {path.name}: {activity.get('type')} images={len(images)} model={args.model}")
                results, raw_text = classify_activity(client, args.model, payload, activity, images)
                print_results(path, payload, activity, images, results, raw_text)

                if args.write:
                    apply_results(images, results, args.model)
                    mark_filter_meta(payload, args.model)
                    write_json(path, payload)
                    file_changed = True
        else:
            print(f"[file] {path.name}: queued {len(jobs)} activities with workers={workers}")
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = []
                for activity, images in jobs:
                    print(f"[request] {path.name}: {activity.get('type')} images={len(images)} model={args.model}")
                    futures.append(
                        executor.submit(
                            classify_activity_job,
                            args.api_key,
                            args.base_url,
                            args.model,
                            path,
                            payload,
                            activity,
                            images,
                        )
                    )

                for future in as_completed(futures):
                    job_path, job_payload, activity, images, results, raw_text = future.result()
                    print_results(job_path, job_payload, activity, images, results, raw_text)

                    if args.write:
                        apply_results(images, results, args.model)
                        mark_filter_meta(payload, args.model)
                        write_json(path, payload)
                        file_changed = True

        if args.write and file_changed:
            changed_files += 1

    print(
        f"\ndone: activities_processed={processed}, "
        f"files_changed={changed_files}, write={args.write}, workers={workers}"
    )


if __name__ == "__main__":
    main()
