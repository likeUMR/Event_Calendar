import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests

try:
    from image_validation_shared import (
        IMAGE_EXT_RE,
        apply_embed_load_metadata,
        embed_image_loads,
        image_key,
        is_standard_image_url,
    )
except ModuleNotFoundError:
    from 获取数据.image_validation_shared import (
        IMAGE_EXT_RE,
        apply_embed_load_metadata,
        embed_image_loads,
        image_key,
        is_standard_image_url,
    )


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIRS = [
    ROOT / "数据" / "活动信息",
    ROOT / "数据" / "活动信息_人工",
]
DEFAULT_CLEAN_LOG = ROOT / "数据" / "image_clean_log.jsonl"

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
}


def parse_args():
    parser = argparse.ArgumentParser(description="清理活动信息 JSON 里的噪声图片和重复图片。")
    parser.add_argument(
        "--dir",
        dest="dirs",
        type=Path,
        action="append",
        help="要清理的目录；默认清理 数据/活动信息 和 数据/活动信息_人工",
    )
    parser.add_argument("--rank", type=int, nargs="*", help="只处理指定 rank")
    parser.add_argument("--write", action="store_true", help="实际写回文件；不加时只预览")
    parser.add_argument("--check-remote", action="store_true", help="实际请求图片 URL，删除无法加载的图片")
    parser.add_argument("--check-embed", action="store_true", help="用 Playwright 按前端 <img> 真实嵌入方式验证图片是否可显示")
    parser.add_argument("--clean-log", type=Path, default=DEFAULT_CLEAN_LOG, help="清洗逐图片记录 JSONL")
    parser.add_argument("--no-clean-log", action="store_true", help="关闭清洗逐图片记录")
    parser.add_argument("--remote-timeout", type=float, default=8.0, help="远程图片检查超时秒数")
    parser.add_argument("--slow-threshold-ms", type=int, default=3000, help="远程图片加载超过该毫秒数时写入 long_load 标记")
    parser.add_argument("--embed-timeout-ms", type=int, default=15000, help="Playwright 嵌入图片校验的单图超时毫秒数")
    parser.add_argument(
        "--embed-referer",
        default="http://127.0.0.1:8000/可视化数据/manual.html",
        help="Playwright 嵌入图片校验时模拟前端页面的 Referer",
    )
    parser.add_argument("--headed", action="store_true", help="Playwright 校验时显示浏览器")
    parser.add_argument("--browser-channel", default=None, help="Playwright 浏览器 channel，例如 chrome 或 msedge")
    parser.add_argument(
        "--dedupe-scope",
        choices=["list", "file"],
        default="list",
        help="去重范围：list 仅同一图片数组内去重，file 在同一 JSON 文件内全局去重",
    )
    return parser.parse_args()


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_clean_log(path, event):
    if not path:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "logged_at": datetime.now(timezone.utc).isoformat(),
        **event,
    }
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")


def is_valid_image_url(url):
    return is_standard_image_url(url, allow_no_ext=True)


def remote_image_loads(url, timeout, slow_threshold_ms):
    started_at = time.perf_counter()
    try:
        response = requests.get(url, headers=REQUEST_HEADERS, timeout=timeout, allow_redirects=True)
    except requests.RequestException:
        elapsed_ms = round((time.perf_counter() - started_at) * 1000)
        return {
            "ok": False,
            "load_time_ms": elapsed_ms,
            "long_load": elapsed_ms > slow_threshold_ms,
        }
    with response:
        elapsed_ms = round((time.perf_counter() - started_at) * 1000)
        if response.status_code >= 400:
            return {
                "ok": False,
                "load_time_ms": elapsed_ms,
                "long_load": elapsed_ms > slow_threshold_ms,
            }
        content_type = response.headers.get("content-type", "").lower()
        if content_type.startswith("image/"):
            return {
                "ok": True,
                "load_time_ms": elapsed_ms,
                "long_load": elapsed_ms > slow_threshold_ms,
                "content_type": content_type,
                "checked_at": datetime.now(timezone.utc).isoformat(),
            }
        if "octet-stream" in content_type and IMAGE_EXT_RE.search(urlparse(response.url).path):
            return {
                "ok": True,
                "load_time_ms": elapsed_ms,
                "long_load": elapsed_ms > slow_threshold_ms,
                "content_type": content_type,
                "checked_at": datetime.now(timezone.utc).isoformat(),
            }
        return {
            "ok": False,
            "load_time_ms": elapsed_ms,
            "long_load": elapsed_ms > slow_threshold_ms,
        }


def apply_remote_load_metadata(image, result):
    image["image_load_check"] = {
        "method": "clean_activity_images_remote_check",
        "checked_at": result.get("checked_at") or datetime.now(timezone.utc).isoformat(),
        "load_time_ms": result.get("load_time_ms"),
        "long_load": bool(result.get("long_load")),
    }
    if result.get("content_type"):
        image["image_load_check"]["content_type"] = result["content_type"]


def log_image_action(log_path, file_path, payload, context, image, action, reason, extra=None):
    url = image.get("url") if isinstance(image, dict) else None
    write_clean_log(
        log_path,
        {
            "event": "image_clean_action",
            "file": file_path.name,
            "rank": payload.get("rank"),
            "game_name": payload.get("name"),
            "section": context.get("section"),
            "context_label": context.get("label"),
            "action": action,
            "reason": reason,
            "url": url,
            "host": urlparse(url).netloc.lower() if url else "",
            "image": image if isinstance(image, dict) else None,
            **(extra or {}),
        },
    )


def image_arrays(payload):
    for source in payload.get("sources") or []:
        if isinstance(source, dict) and isinstance(source.get("images"), list):
            yield {
                "section": "sources",
                "label": source.get("source_title") or source.get("title") or source.get("source_url") or "source",
            }, source["images"]
    for page in payload.get("event_detail_pages") or []:
        if isinstance(page, dict) and isinstance(page.get("images"), list):
            yield {
                "section": "event_detail_pages",
                "label": page.get("source_title") or page.get("title") or page.get("source_url") or page.get("url") or "detail_page",
            }, page["images"]
    for event in payload.get("event_catalog") or []:
        if isinstance(event, dict) and isinstance(event.get("images"), list):
            yield {
                "section": "event_catalog",
                "label": event.get("display_name") or event.get("title") or event.get("type") or "catalog_event",
            }, event["images"]
    for activity in payload.get("activity_types") or []:
        if isinstance(activity, dict) and isinstance(activity.get("images"), list):
            yield {
                "section": "activity_types",
                "label": activity.get("display_name") or activity.get("title") or activity.get("type") or "activity_type",
            }, activity["images"]
    for key in ("screenshots_or_images", "screenshot_or_visual_references"):
        if isinstance(payload.get(key), list):
            yield {
                "section": key,
                "label": key,
            }, payload[key]


def clean_image_list(
    file_path,
    payload,
    context,
    images,
    file_seen,
    check_remote,
    check_embed,
    remote_timeout,
    embed_timeout_ms,
    remote_cache,
    embed_cache,
    embed_page,
    slow_threshold_ms,
    clean_log,
):
    kept = []
    removed_noise = 0
    removed_duplicate = 0
    removed_unavailable = 0
    marked_long_load = 0
    list_seen = set()
    for image in images:
        if not isinstance(image, dict):
            removed_noise += 1
            log_image_action(clean_log, file_path, payload, context, {"url": None}, "remove", "non_dict_image")
            continue
        url = image.get("url")
        if not is_valid_image_url(url):
            removed_noise += 1
            log_image_action(clean_log, file_path, payload, context, image, "remove", "invalid_image_url")
            continue
        key = image_key(url)
        if key in list_seen or key in file_seen:
            removed_duplicate += 1
            log_image_action(clean_log, file_path, payload, context, image, "remove", "duplicate_image")
            continue
        if check_embed:
            if url not in embed_cache:
                embed_cache[url] = embed_image_loads(embed_page, url, embed_timeout_ms, slow_threshold_ms)
            result = embed_cache[url]
            if not result.get("ok"):
                removed_unavailable += 1
                log_image_action(
                    clean_log,
                    file_path,
                    payload,
                    context,
                    image,
                    "remove",
                    "embed_unavailable",
                    {"image_load_check": result},
                )
                continue
            apply_embed_load_metadata(image, result)
            if result.get("long_load"):
                marked_long_load += 1
                log_image_action(
                    clean_log,
                    file_path,
                    payload,
                    context,
                    image,
                    "mark",
                    "long_load",
                    {"image_load_check": result},
                )
        elif check_remote:
            if url not in remote_cache:
                remote_cache[url] = remote_image_loads(url, remote_timeout, slow_threshold_ms)
            result = remote_cache[url]
            if not result.get("ok"):
                removed_unavailable += 1
                log_image_action(
                    clean_log,
                    file_path,
                    payload,
                    context,
                    image,
                    "remove",
                    "remote_unavailable",
                    {"image_load_check": result},
                )
                continue
            apply_remote_load_metadata(image, result)
            if result.get("long_load"):
                marked_long_load += 1
                log_image_action(
                    clean_log,
                    file_path,
                    payload,
                    context,
                    image,
                    "mark",
                    "long_load",
                    {"image_load_check": result},
                )
        list_seen.add(key)
        file_seen.add(key)
        kept.append(image)
    if len(kept) != len(images):
        images[:] = kept
    return removed_noise, removed_duplicate, removed_unavailable, marked_long_load


def clean_payload(
    file_path,
    payload,
    dedupe_scope,
    check_remote,
    check_embed,
    remote_timeout,
    embed_timeout_ms,
    remote_cache,
    embed_cache,
    embed_page,
    slow_threshold_ms,
    clean_log,
    action_label,
):
    removed_noise = 0
    removed_duplicate = 0
    removed_unavailable = 0
    marked_long_load = 0
    file_seen = set()
    for context, images in image_arrays(payload):
        seen = file_seen if dedupe_scope == "file" else set()
        noise, duplicate, unavailable, long_load = clean_image_list(
            file_path,
            payload,
            context,
            images,
            seen,
            check_remote,
            check_embed,
            remote_timeout,
            embed_timeout_ms,
            remote_cache,
            embed_cache,
            embed_page,
            slow_threshold_ms,
            clean_log,
        )
        removed_noise += noise
        removed_duplicate += duplicate
        removed_unavailable += unavailable
        marked_long_load += long_load
        if noise or duplicate or unavailable or long_load:
            print(
                f"[{action_label}-item] {file_path.name} :: {context.get('section')} :: {context.get('label')} :: "
                f"remove_noise={noise}, remove_duplicate={duplicate}, remove_unavailable={unavailable}, "
                f"mark_long_load={long_load}",
                flush=True,
            )
    return removed_noise, removed_duplicate, removed_unavailable, marked_long_load


def iter_json_files(dirs, ranks):
    rank_set = set(ranks or [])
    for directory in dirs:
        for path in sorted(directory.glob("*.json")):
            payload = load_json(path)
            if rank_set and int(payload.get("rank", -1)) not in rank_set:
                continue
            yield path, payload


def main():
    args = parse_args()
    dirs = args.dirs or DEFAULT_DIRS
    clean_log = None if args.no_clean_log else args.clean_log
    totals = {"files_changed": 0, "noise": 0, "duplicate": 0, "unavailable": 0, "long_load": 0}
    remote_cache = {}
    embed_cache = {}
    embed_page = None
    browser = None
    context = None
    if args.check_embed:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as error:
            raise RuntimeError("缺少 playwright。请先运行：pip install playwright && python -m playwright install chromium") from error
        playwright = sync_playwright().start()
        launch_options = {"headless": not args.headed}
        if args.browser_channel:
            launch_options["channel"] = args.browser_channel
        browser = playwright.chromium.launch(**launch_options)
        context = browser.new_context(extra_http_headers={"Referer": args.embed_referer})
        embed_page = context.new_page()
        embed_page.goto("data:text/html,<html><body></body></html>", wait_until="domcontentloaded")
    else:
        playwright = None
    try:
        action = "write" if args.write else "dry-run"
        for path, payload in iter_json_files(dirs, args.rank):
            noise, duplicate, unavailable, long_load = clean_payload(
                path,
                payload,
                args.dedupe_scope,
                args.check_remote,
                args.check_embed,
                args.remote_timeout,
                args.embed_timeout_ms,
                remote_cache,
                embed_cache,
                embed_page,
                args.slow_threshold_ms,
                clean_log,
                action,
            )
            if not noise and not duplicate and not unavailable and not long_load:
                continue
            totals["files_changed"] += 1
            totals["noise"] += noise
            totals["duplicate"] += duplicate
            totals["unavailable"] += unavailable
            totals["long_load"] += long_load
            print(
                f"[{action}] {path.name}: "
                f"remove_noise={noise}, remove_duplicate={duplicate}, remove_unavailable={unavailable}, "
                f"mark_long_load={long_load}"
            )
            if args.write:
                write_json(path, payload)
    finally:
        if context:
            context.close()
        if browser:
            browser.close()
        if playwright:
            playwright.stop()
    print(
        "done: "
        f"files_changed={totals['files_changed']}, "
        f"removed_noise={totals['noise']}, "
        f"removed_duplicate={totals['duplicate']}, "
        f"removed_unavailable={totals['unavailable']}, "
        f"marked_long_load={totals['long_load']}, "
        f"remote_checked={len(remote_cache)}, "
        f"embed_checked={len(embed_cache)}, "
        f"write={args.write}"
    )


if __name__ == "__main__":
    main()
