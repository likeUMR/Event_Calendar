import argparse
import html
import os
import json
import re
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

import requests

try:
    from image_validation_shared import (
        IMAGE_EXT_RE,
        NON_IMAGE_EXT_RE,
        apply_embed_load_metadata,
        embed_image_loads,
        image_key as dedupe_key,
        is_google_thumbnail_url,
        is_standard_image_url,
    )
except ModuleNotFoundError:
    from 获取数据.image_validation_shared import (
        IMAGE_EXT_RE,
        NON_IMAGE_EXT_RE,
        apply_embed_load_metadata,
        embed_image_loads,
        image_key as dedupe_key,
        is_google_thumbnail_url,
        is_standard_image_url,
    )


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_DIR = ROOT / "数据" / "活动信息_人工"
DEFAULT_IMAGE_DEBUG_LOG = ROOT / "数据" / "image_supplement_debug.jsonl"
GOOGLE_IMAGE_SEARCH = "https://www.google.com/search?tbm=isch&udm=2&q={query}"
GOOGLE_CUSTOM_SEARCH_API = "https://www.googleapis.com/customsearch/v1"
APPLE_STORE_SEARCH_API = "https://itunes.apple.com/search"
GOOGLE_PLAY_SEARCH = "https://play.google.com/store/search"
GOOGLE_PLAY_DETAILS = "https://play.google.com/store/apps/details"
ORIGINAL_METHOD = "original_manual_json"
SUPPLEMENT_METHOD = "bulk_google_image_search"
STORE_SUPPLEMENT_METHOD = "bulk_us_store_screenshot_search"
GOOGLE_INITIAL_WAIT_MS = 1200
GOOGLE_EXPAND_SIGNAL_TIMEOUT_MS = 1200
GOOGLE_EXPAND_FALLBACK_WAIT_MS = 350
GOOGLE_CLOSE_PANEL_WAIT_MS = 250
GOOGLE_RELOAD_WAIT_MS = 900
SOURCE_PAGE_FETCH_TIMEOUT = 8
IMAGE_AVAILABILITY_TIMEOUT = 4
EMBED_CHECK_BATCH_SIZE = 5


def parse_args():
    parser = argparse.ArgumentParser(
        description="为活动信息 JSON 中缺少图片的活动类型批量补充 Google 图片搜索结果。"
    )
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR, help="人工活动 JSON 目录")
    parser.add_argument("--rank", type=int, nargs="*", help="只处理指定 rank，例如 --rank 1 3 5")
    parser.add_argument("--max-images", type=int, default=5, help="每个缺图活动写入的图片数量")
    parser.add_argument("--delay", type=float, default=1.5, help="每次 Google 请求之间的间隔秒数")
    parser.add_argument("--dry-run", action="store_true", help="只打印计划，不写文件、不请求 Google")
    parser.add_argument("--google-api-key", default=os.environ.get("GOOGLE_API_KEY"), help="Google Custom Search API key；也可用环境变量 GOOGLE_API_KEY")
    parser.add_argument("--google-cse-id", default=os.environ.get("GOOGLE_CSE_ID"), help="Google Programmable Search Engine cx；也可用环境变量 GOOGLE_CSE_ID")
    parser.add_argument(
        "--activity-image-source",
        choices=["auto", "google-api", "playwright"],
        default="auto",
        help="活动级补图来源；auto 会优先 Google API，未配置 key 时使用 Playwright 浏览器搜索",
    )
    parser.add_argument("--headed", action="store_true", help="Playwright 搜图时显示浏览器窗口")
    parser.add_argument("--browser-user-data-dir", type=Path, help="Playwright 持久化浏览器目录；适合手动通过 Google 验证后复用")
    parser.add_argument("--browser-channel", default=None, help="Playwright 浏览器 channel，例如 chrome 或 msedge")
    parser.add_argument("--browser-timeout", type=int, default=25000, help="Playwright 页面超时毫秒数")
    parser.add_argument("--manual-verification-timeout", type=int, default=180000, help="Google 验证页人工处理等待毫秒数")
    parser.add_argument("--embed-timeout-ms", type=int, default=15000, help="前端嵌入式图片校验单图超时毫秒数")
    parser.add_argument("--embed-slow-threshold-ms", type=int, default=3000, help="嵌入式图片加载超过该毫秒数时写入 long_load 标记")
    parser.add_argument("--activity-image-budget-seconds", type=float, default=120.0, help="单个活动补图总预算秒数；超时则停止继续拉取下一批候选")
    parser.add_argument("--embed-referer", default="http://127.0.0.1:8000/可视化数据/manual.html", help="嵌入式图片校验时模拟前端页面的 Referer")
    parser.add_argument("--skip-embed-validation", action="store_true", help="跳过前端嵌入式图片校验，直接沿用现有 URL/可达性筛选")
    parser.add_argument("--image-debug-log", type=Path, default=DEFAULT_IMAGE_DEBUG_LOG, help="逐候选图片调试日志 JSONL")
    parser.add_argument("--no-image-debug-log", action="store_true", help="关闭逐候选图片调试日志")
    parser.add_argument("--skip-activity-images", action="store_true", help="不补活动级图片")
    parser.add_argument("--skip-store-images", action="store_true", help="不补游戏级商店截图")
    parser.add_argument(
        "--store-source",
        choices=["auto", "apple", "google-play"],
        default="auto",
        help="游戏级商店截图来源；默认先 Apple 美区，失败后 Google Play 美区",
    )
    parser.add_argument(
        "--refresh-existing-supplement",
        action="store_true",
        help="已由批量搜索补充过的活动也重新搜索覆盖；默认只处理 images 为空的活动",
    )
    return parser.parse_args()


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_debug_log(path, event):
    if not path:
        return
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    event = {"logged_at": datetime.now(timezone.utc).isoformat(), **event}
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")


def image_method(image):
    return image.get("collection_method") or image.get("source_method") or image.get("image_source")


def is_activity_supplement_image(image):
    method = image_method(image)
    return isinstance(method, str) and method.startswith(SUPPLEMENT_METHOD)


def valid_activity_supplement_images(activity):
    images = activity.get("images") or []
    return [
        image
        for image in images
        if isinstance(image, dict)
        and is_activity_supplement_image(image)
        and is_standard_image_url(image.get("url"), allow_no_ext=True)
    ]


def normalize_name(value):
    return re.sub(r"[^a-z0-9]+", "", (value or "").lower())


def normalize_query_game_name(value):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]+", " ", (value or "").lower())).strip()


def normalize_query_activity_type(value):
    return re.sub(r"\s+", " ", (value or "").replace("_", " ").strip().lower())


def has_original_images(activity):
    for image in activity.get("images") or []:
        if not is_activity_supplement_image(image):
            return True
    return False


def should_supplement(activity, refresh_existing_supplement, max_images):
    if refresh_existing_supplement:
        return True
    return len(valid_activity_supplement_images(activity)) < max_images


def mark_existing_images(activity):
    changed = False
    for image in activity.get("images") or []:
        if not isinstance(image, dict):
            continue
        if not image_method(image):
            image["collection_method"] = ORIGINAL_METHOD
            image["image_source_type"] = "original"
            changed = True
    return changed


def prune_invalid_activity_supplement_images(activity):
    images = activity.get("images") or []
    kept = []
    changed = False
    seen = set()
    for image in images:
        if not isinstance(image, dict) or not is_activity_supplement_image(image):
            kept.append(image)
            continue
        url = image.get("url")
        key = dedupe_key(url or "")
        if not is_standard_image_url(url, allow_no_ext=True) or key in seen:
            changed = True
            continue
        seen.add(key)
        kept.append(image)
    if changed:
        activity["images"] = kept
    return changed


def mark_existing_visual_references(game):
    changed = False
    for item in game.get("screenshot_or_visual_references") or []:
        if not isinstance(item, dict):
            continue
        if not image_method(item):
            item["collection_method"] = ORIGINAL_METHOD
            item["image_source_type"] = "original"
            changed = True
    return changed


def activity_query(game_name, activity):
    parts = [
        normalize_query_game_name(game_name),
        normalize_query_activity_type(activity.get("type") or ""),
    ]
    return " ".join(part for part in parts if part)


def google_search_url(query):
    return GOOGLE_IMAGE_SEARCH.format(query=quote_plus(query))


def normalize_url(raw):
    if not raw:
        return None
    url = raw.replace("\\/", "/")
    url = bytes(url, "utf-8").decode("unicode_escape", errors="ignore")
    url = unquote(url)
    if not url.startswith(("http://", "https://")):
        return None
    if not is_valid_image_url(url):
        return None
    return url


def orientation(width, height):
    if not width or not height:
        return "unknown"
    ratio = width / height
    if ratio >= 1.15:
        return "landscape"
    if ratio <= 0.87:
        return "portrait"
    return "square"


def shape_info(width, height):
    ratio = round(width / height, 4) if width and height else None
    return {
        "width": width,
        "height": height,
        "aspect_ratio": ratio,
        "orientation": orientation(width, height),
    }


def parse_dimensions_from_url(url):
    parsed = urlparse(url or "")
    params = parse_qs(parsed.query)
    for width_key, height_key in (("width", "height"), ("w", "h")):
        width_values = params.get(width_key) or []
        height_values = params.get(height_key) or []
        if width_values and height_values and width_values[0].isdigit() and height_values[0].isdigit():
            return int(width_values[0]), int(height_values[0])
    google_play_size = re.search(r"[=/-]w(\d{2,5})-h(\d{2,5})(?:[-/?#]|$)", url or "")
    if google_play_size:
        return int(google_play_size.group(1)), int(google_play_size.group(2))
    matches = re.findall(r"(?<!\d)(\d{2,5})x(\d{2,5})(?!\d)", url or "")
    if not matches:
        return None, None
    width, height = matches[-1]
    return int(width), int(height)


def parse_dimensions_from_text(text):
    match = re.search(r"(?<!\d)(\d{2,5})\s*[×x]\s*(\d{2,5})(?!\d)", text or "")
    if not match:
        return None, None
    return int(match.group(1)), int(match.group(2))


def youtube_video_id(url):
    parsed = urlparse(url or "")
    host = parsed.netloc.lower()
    if "youtu.be" in host:
        return parsed.path.strip("/").split("/")[0] or None
    if "youtube.com" in host:
        return (parse_qs(parsed.query).get("v") or [None])[0]
    return None


def source_page_image_candidates(source_url, page_html):
    candidates = []
    video_id = youtube_video_id(source_url)
    if video_id:
        candidates.append((f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg", None, None))
        candidates.append((f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg", None, None))

    attr_patterns = [
        r'<meta[^>]+(?:property|name)=["\'](?:og:image|og:image:secure_url|twitter:image|twitter:image:src)["\'][^>]+content=["\'](?P<url>[^"\']+)["\']',
        r'<meta[^>]+content=["\'](?P<url>[^"\']+)["\'][^>]+(?:property|name)=["\'](?:og:image|og:image:secure_url|twitter:image|twitter:image:src)["\']',
        r'<link[^>]+rel=["\'][^"\']*image_src[^"\']*["\'][^>]+href=["\'](?P<url>[^"\']+)["\']',
    ]
    for pattern in attr_patterns:
        for match in re.finditer(pattern, page_html or "", re.I):
            candidates.append((html.unescape(match.group("url")), None, None))

    for match in re.finditer(r'"(?:image|thumbnailUrl|contentUrl)"\s*:\s*"(?P<url>https?:\/\/[^"]+)"', page_html or "", re.I):
        candidates.append((html.unescape(match.group("url").replace("\\/", "/")), None, None))

    return [(url, None, None) for url, _, _ in candidates]


def is_image_response(response):
    content_type = (response.headers.get("content-type") or "").lower()
    return response.status_code < 400 and content_type.startswith("image/")


def image_url_is_reachable(url, already_loaded=False):
    if already_loaded:
        return True
    if not is_standard_image_url(url, allow_no_ext=True):
        return False

    headers = request_headers()
    try:
        response = requests.head(
            url,
            headers=headers,
            timeout=IMAGE_AVAILABILITY_TIMEOUT,
            allow_redirects=True,
        )
        if is_image_response(response):
            return True
        if response.status_code not in (403, 405):
            return False
    except requests.RequestException:
        pass

    try:
        response = requests.get(
            url,
            headers={**headers, "Range": "bytes=0-0"},
            timeout=IMAGE_AVAILABILITY_TIMEOUT,
            allow_redirects=True,
            stream=True,
        )
        try:
            return is_image_response(response)
        finally:
            response.close()
    except requests.RequestException:
        return False


def fetch_source_page_image(card):
    source_url = card.get("source_url")
    if not source_url or not source_url.startswith(("http://", "https://")):
        return None

    direct_candidates = source_page_image_candidates(source_url, "")
    if direct_candidates and youtube_video_id(source_url):
        candidates = direct_candidates
    else:
        response = requests.get(
            source_url,
            headers=request_headers(),
            timeout=SOURCE_PAGE_FETCH_TIMEOUT,
            allow_redirects=True,
        )
        response.raise_for_status()
        candidates = source_page_image_candidates(source_url, response.text)

    for url, width, height in candidates:
        if not is_standard_image_url(url, allow_no_ext=True):
            continue
        if not image_url_is_reachable(url):
            continue
        if not width or not height:
            width, height = parse_dimensions_from_url(url)
        if not width or not height:
            width = card.get("width")
            height = card.get("height")
        return {
            "url": url,
            "context_url": source_url,
            "title": card.get("alt") or "",
            **shape_info(int(width) if width else None, int(height) if height else None),
        }
    return None


def prefetch_source_page_images(cards, max_images):
    if not cards or max_images <= 0:
        return {}
    indexed_results = {}
    with ThreadPoolExecutor(max_workers=min(5, max_images, len(cards))) as executor:
        futures = {
            executor.submit(fetch_source_page_image, card): index
            for index, card in enumerate(cards[:max_images])
            if card.get("source_url")
        }
        for future in as_completed(futures):
            try:
                image = future.result()
            except Exception:
                continue
            if image:
                indexed_results[futures[future]] = image
    return {index: indexed_results[index] for index in sorted(indexed_results)}


def google_image_params(raw_url):
    parsed = urlparse(raw_url or "")
    params = parse_qs(parsed.query)
    imgurl = normalize_expanded_image_url((params.get("imgurl") or [None])[0])
    imgrefurl = (params.get("imgrefurl") or [None])[0]
    return imgurl, imgrefurl


def wait_for_expanded_image_signal(page):
    try:
        page.wait_for_function(
            """
            () => performance.getEntriesByType('resource').some((entry) => entry.name.includes('imgurl='))
              || Array.from(document.links).some((link) => (link.href || '').includes('imgurl='))
            """,
            timeout=GOOGLE_EXPAND_SIGNAL_TIMEOUT_MS,
        )
    except Exception:
        page.wait_for_timeout(GOOGLE_EXPAND_FALLBACK_WAIT_MS)


def close_google_image_viewer(page):
    try:
        page.keyboard.press("Escape")
        page.wait_for_timeout(GOOGLE_CLOSE_PANEL_WAIT_MS)
    except Exception:
        pass

    for label in ("Close", "关闭"):
        try:
            page.get_by_role("button", name=re.compile(label, re.I)).click(timeout=500)
            page.wait_for_timeout(GOOGLE_CLOSE_PANEL_WAIT_MS)
            break
        except Exception:
            pass


def normalize_expanded_image_url(raw_url):
    if not raw_url:
        return None
    url = unquote(raw_url.replace("\\/", "/"))
    if not url.startswith(("http://", "https://")):
        return None
    return url


def is_valid_image_url(url):
    return is_standard_image_url(url, allow_no_ext=True)


def parse_google_images(html, max_images):
    candidates = []
    seen = set()

    patterns = [
        re.compile(r'"ou"\s*:\s*"(?P<url>https?://.*?")\s*,\s*"ow"\s*:\s*(?P<w>\d+)\s*,\s*"oh"\s*:\s*(?P<h>\d+)', re.S),
        re.compile(r'\["(?P<url>https?://[^"]+?)"\s*,\s*(?P<w>\d{2,5})\s*,\s*(?P<h>\d{2,5})\]', re.S),
    ]

    for pattern in patterns:
        for match in pattern.finditer(html):
            url = normalize_url(match.group("url").rstrip('"'))
            if not url:
                continue
            key = dedupe_key(url)
            if key in seen:
                continue
            width = int(match.group("w"))
            height = int(match.group("h"))
            if width < 80 or height < 80:
                continue
            seen.add(key)
            candidates.append({"url": url, **shape_info(width, height)})
            if len(candidates) >= max_images:
                return candidates

    for raw_url in re.findall(r'https?://[^"\\<> ]+', html):
        url = normalize_url(raw_url)
        if not url:
            continue
        key = dedupe_key(url)
        if key in seen:
            continue
        seen.add(key)
        candidates.append({"url": url, **shape_info(None, None)})
        if len(candidates) >= max_images:
            break

    return candidates


def search_google_images(query, max_images):
    raise RuntimeError(
        "Google 静态图片页通常不再返回可稳定解析的原图列表。请使用 --google-api-key 和 --google-cse-id，"
        "或使用 --activity-image-source playwright 通过浏览器自动化搜索。"
    )


def search_google_images_api(query, max_images, api_key, cse_id):
    if not api_key or not cse_id:
        return search_google_images(query, max_images)

    params = {
        "key": api_key,
        "cx": cse_id,
        "q": query,
        "searchType": "image",
        "num": min(max_images, 10),
        "safe": "off",
    }
    response = requests.get(GOOGLE_CUSTOM_SEARCH_API, params=params, timeout=25)
    response.raise_for_status()
    payload = response.json()
    search_url = google_search_url(query)
    results = []
    seen = set()
    for item in payload.get("items") or []:
        url = item.get("link")
        if not url or not url.startswith(("http://", "https://")):
            continue
        key = dedupe_key(url)
        if key in seen:
            continue
        seen.add(key)
        image_meta = item.get("image") or {}
        width = image_meta.get("width")
        height = image_meta.get("height")
        try:
            width = int(width) if width else None
            height = int(height) if height else None
        except (TypeError, ValueError):
            width = None
            height = None
        results.append(
            {
                "url": url,
                "context_url": image_meta.get("contextLink") or item.get("image", {}).get("thumbnailLink"),
                "title": item.get("title") or "",
                **shape_info(width, height),
            }
        )
        if len(results) >= max_images:
            break
    return search_url, results


def looks_like_search_image(url):
    return is_valid_image_url(url)


def search_google_images_playwright(
    query,
    max_images,
    headed=False,
    timeout=25000,
    user_data_dir=None,
    browser_channel=None,
    manual_verification_timeout=180000,
    image_debug_log=None,
    do_embed_validation=False,
    embed_timeout_ms=15000,
    embed_slow_threshold_ms=3000,
):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as error:
        raise RuntimeError("缺少 playwright。请先运行：pip install playwright && python -m playwright install chromium") from error

    started_at = time.perf_counter()
    search_url = google_search_url(query)
    results = []
    seen = set()
    attempted_cards = 0
    skip_reasons = Counter()

    with sync_playwright() as playwright:
        launch_options = {
            "headless": not headed,
        }
        if browser_channel:
            launch_options["channel"] = browser_channel
        context_options = {
            "locale": "en-US",
            "viewport": {"width": 1365, "height": 900},
            "user_agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0 Safari/537.36"
            ),
        }
        if user_data_dir:
            context = playwright.chromium.launch_persistent_context(
                str(user_data_dir),
                **launch_options,
                **context_options,
            )
            page = context.pages[0] if context.pages else context.new_page()
            browser = None
        else:
            browser = playwright.chromium.launch(**launch_options)
            context = browser.new_context(**context_options)
            page = context.new_page()
        embed_page = context.new_page() if do_embed_validation else None
        page.set_default_timeout(timeout)
        page.goto(search_url, wait_until="domcontentloaded")
        if "/sorry/" in page.url:
            if not headed:
                context.close()
                if browser:
                    browser.close()
                raise RuntimeError(
                    "Google 返回了异常流量验证页。请改用 --headed --browser-user-data-dir .browser-profile "
                    "拉起可见浏览器并手动通过验证，或使用 Google Custom Search API。"
                )
            print("[manual] Google verification page opened. Finish it in the browser window; the script will continue automatically.")
            try:
                page.wait_for_url(lambda url: "/sorry/" not in url, timeout=manual_verification_timeout)
            except Exception as error:
                context.close()
                if browser:
                    browser.close()
                raise RuntimeError("Google 验证等待超时；请重新运行并完成浏览器里的验证。") from error
            page.goto(search_url, wait_until="domcontentloaded")

        for label in ("Accept all", "I agree", "全部接受", "同意"):
            try:
                page.get_by_role("button", name=re.compile(label, re.I)).click(timeout=1500)
                break
            except Exception:
                pass

        page.wait_for_timeout(GOOGLE_INITIAL_WAIT_MS)

        loaded_image_resources = set()

        def remember_image_response(response):
            try:
                content_type = (response.headers.get("content-type") or "").lower()
            except Exception:
                return
            if content_type.startswith("image/"):
                loaded_image_resources.add(response.url)

        page.on("response", remember_image_response)

        initial_cards = page.evaluate(
            """
            () => Array.from(document.images)
            .map((img, index) => {
              const rect = img.getBoundingClientRect();
              const card = img.closest('[data-docid][data-lpage]');
              const ad = img.closest('.pla-unit, .pla-unit-container, [aria-label="Ads"], [aria-label*="Sponsored"]');
              return {
                index,
                url: img.currentSrc || img.src || img.getAttribute('data-src') || '',
                source_url: card ? card.getAttribute('data-lpage') : '',
                docid: card ? card.getAttribute('data-docid') : '',
                is_ad: !!ad,
                alt: img.alt || '',
                width: Math.max(img.naturalWidth || 0, Math.round(rect.width) || 0) || null,
                height: Math.max(img.naturalHeight || 0, Math.round(rect.height) || 0) || null,
                row: Math.round(rect.top / 80),
                left: rect.left,
                visible: rect.width > 80
                  && rect.height > 80
                  && rect.bottom > 0
                  && rect.right > 0
                  && rect.top < window.innerHeight
                  && rect.left < window.innerWidth
              };
            })
            .filter((img) => img.visible && img.docid && img.source_url && !img.is_ad)
            .sort((a, b) => a.row - b.row || a.left - b.left)
            """
        )

        prefetched_images = {}
        for card_index, image in prefetch_source_page_images(initial_cards, max_images).items():
            card = initial_cards[card_index]
            card_key = dedupe_key(card.get("url") or card.get("alt") or str(card.get("index")))
            prefetched_images[card_key] = image

        processed_cards = set()
        rejected_candidate_keys = set()
        attempts = 0
        while len(results) < max_images and attempts < max_images * 4:
            attempts += 1
            cards = page.evaluate(
                """
                () => Array.from(document.images)
                .map((img, index) => {
                  const rect = img.getBoundingClientRect();
                  const card = img.closest('[data-docid][data-lpage]');
                  const ad = img.closest('.pla-unit, .pla-unit-container, [aria-label="Ads"], [aria-label*="Sponsored"]');
                  return {
                    index,
                    url: img.currentSrc || img.src || img.getAttribute('data-src') || '',
                    source_url: card ? card.getAttribute('data-lpage') : '',
                    docid: card ? card.getAttribute('data-docid') : '',
                    is_ad: !!ad,
                    alt: img.alt || '',
                    width: Math.max(img.naturalWidth || 0, Math.round(rect.width) || 0) || null,
                    height: Math.max(img.naturalHeight || 0, Math.round(rect.height) || 0) || null,
                    displayWidth: Math.round(rect.width) || 0,
                    displayHeight: Math.round(rect.height) || 0,
                    top: rect.top,
                    left: rect.left,
                    x: Math.round(rect.left + rect.width / 2),
                    y: Math.round(rect.top + rect.height / 2),
                    row: Math.round(rect.top / 80),
                    visible: rect.width > 80
                      && rect.height > 80
                      && rect.bottom > 0
                      && rect.right > 0
                      && rect.top < window.innerHeight
                      && rect.left < window.innerWidth
                  };
                })
                .filter((img) => img.visible && img.docid && img.source_url && !img.is_ad)
                .sort((a, b) => a.row - b.row || a.left - b.left)
                """
            )
            card = None
            used_prefetch = False
            for candidate in cards:
                card_key = dedupe_key(candidate.get("url") or candidate.get("alt") or str(candidate.get("index")))
                if card_key not in processed_cards:
                    processed_cards.add(card_key)
                    prefetched_image = prefetched_images.get(card_key)
                    if prefetched_image:
                        image_key = dedupe_key(prefetched_image["url"])
                        if image_key not in seen:
                            embed_result = None
                            if do_embed_validation and embed_page is not None:
                                embed_result = embed_image_loads(
                                    embed_page,
                                    prefetched_image["url"],
                                    embed_timeout_ms,
                                    embed_slow_threshold_ms,
                                )
                                if not embed_result.get("ok"):
                                    skip_reasons["embed_unavailable"] += 1
                                    write_debug_log(
                                        image_debug_log,
                                        {
                                            "event": "image_candidate_skip",
                                            "query": query,
                                            "reason": "embed_unavailable",
                                            "candidate_url": prefetched_image["url"],
                                            "candidate_context_url": prefetched_image.get("context_url") or "",
                                            "candidate_title": prefetched_image.get("title") or "",
                                            "card_title": candidate.get("alt") or "",
                                            "card_source_url": candidate.get("source_url") or "",
                                            "card_docid": candidate.get("docid") or "",
                                            "source": "prefetch",
                                            "image_load_check": embed_result,
                                        },
                                    )
                                    card = candidate
                                    continue
                                prefetched_image["image_load_check"] = embed_result
                            seen.add(image_key)
                            results.append(prefetched_image)
                            used_prefetch = True
                            break
                        skip_reasons["duplicate"] += 1
                        write_debug_log(
                            image_debug_log,
                            {
                                "event": "image_candidate_skip",
                                "query": query,
                                "reason": "duplicate",
                                "candidate_url": prefetched_image["url"],
                                "candidate_context_url": prefetched_image.get("context_url") or "",
                                "candidate_title": prefetched_image.get("title") or "",
                                "card_title": candidate.get("alt") or "",
                                "card_source_url": candidate.get("source_url") or "",
                                "card_docid": candidate.get("docid") or "",
                                "source": "prefetch",
                            },
                        )
                    card = candidate
                    break
            if used_prefetch:
                continue
            if not card:
                break
            attempted_cards += 1
            accepted = False
            accepted_card = False
            card_log = {
                "event": "image_candidate_skip",
                "query": query,
                "card_title": card.get("alt") or "",
                "card_source_url": card.get("source_url") or "",
                "card_docid": card.get("docid") or "",
                "card_attempt": attempted_cards,
                "card_top": card.get("top"),
                "card_left": card.get("left"),
            }
            try:
                page.evaluate("performance.clearResourceTimings()")
            except Exception:
                pass
            loaded_image_resources.clear()
            page.mouse.click(card["x"], card["y"])
            wait_for_expanded_image_signal(page)

            expanded = page.evaluate(
                """
                () => {
                  const links = Array.from(document.links).map((a) => ({
                    href: a.href || '',
                    text: (a.innerText || a.ariaLabel || '').trim()
                  })).filter((item) => item.href);
                  const images = Array.from(document.images).map((img) => {
                    const rect = img.getBoundingClientRect();
                    return {
                      url: img.currentSrc || img.src || img.getAttribute('data-src') || '',
                      alt: img.alt || '',
                      width: Math.max(img.naturalWidth || 0, Math.round(rect.width) || 0) || null,
                      height: Math.max(img.naturalHeight || 0, Math.round(rect.height) || 0) || null,
                      displayArea: (Math.round(rect.width) || 0) * (Math.round(rect.height) || 0),
                      visible: rect.width > 80
                        && rect.height > 80
                        && rect.bottom > 0
                        && rect.right > 0
                        && rect.top < window.innerHeight
                        && rect.left < window.innerWidth
                    };
                  }).filter((img) => img.visible).sort((a, b) => b.displayArea - a.displayArea);
                  const resources = performance.getEntriesByType('resource')
                    .map((entry) => entry.name)
                    .filter(Boolean);
                  return { links, images, resources };
                }
                """
            )

            candidates = []
            link_text_by_url = {}
            for link in expanded.get("links") or []:
                href = link.get("href") or ""
                text = link.get("text") or ""
                link_text_by_url[href] = text
                imgurl, imgrefurl = google_image_params(href)
                if imgurl:
                    candidates.append(
                        {
                            "url": imgurl,
                            "context_url": normalize_expanded_image_url(imgrefurl) or href,
                            "title": card.get("alt") or text,
                            "allow_no_ext": True,
                            "dimension_text": text,
                            "already_loaded": imgurl in loaded_image_resources,
                        }
                    )

            for resource_url in expanded.get("resources") or []:
                imgurl, imgrefurl = google_image_params(resource_url)
                if imgurl:
                    candidates.append(
                        {
                            "url": imgurl,
                            "context_url": normalize_expanded_image_url(imgrefurl) or search_url,
                            "title": card.get("alt") or "",
                            "allow_no_ext": True,
                            "already_loaded": imgurl in loaded_image_resources,
                        }
                    )
                elif resource_url in loaded_image_resources:
                    candidates.append(
                        {
                            "url": resource_url,
                            "context_url": search_url,
                            "title": card.get("alt") or "",
                            "allow_no_ext": True,
                            "already_loaded": True,
                        }
                    )

            for image in expanded.get("images") or []:
                candidates.append(
                    {
                        "url": image.get("url") or "",
                        "context_url": search_url,
                        "title": image.get("alt") or card.get("alt") or "",
                        "width": image.get("width"),
                        "height": image.get("height"),
                        "allow_no_ext": False,
                    }
                )

            for candidate in candidates:
                url = candidate.get("url") or ""
                key = dedupe_key(url)
                if key in rejected_candidate_keys:
                    continue
                if not is_standard_image_url(url, allow_no_ext=candidate.get("allow_no_ext", False)):
                    skip_reasons["non_standard_url"] += 1
                    rejected_candidate_keys.add(key)
                    write_debug_log(
                        image_debug_log,
                        {
                            **card_log,
                            "reason": "non_standard_url",
                            "candidate_url": url,
                            "candidate_context_url": candidate.get("context_url") or "",
                            "candidate_title": candidate.get("title") or "",
                            "already_loaded": bool(candidate.get("already_loaded")),
                        },
                    )
                    continue
                if not image_url_is_reachable(url, candidate.get("already_loaded", False)):
                    skip_reasons["unreachable"] += 1
                    rejected_candidate_keys.add(key)
                    write_debug_log(
                        image_debug_log,
                        {
                            **card_log,
                            "reason": "unreachable",
                            "candidate_url": url,
                            "candidate_context_url": candidate.get("context_url") or "",
                            "candidate_title": candidate.get("title") or "",
                            "already_loaded": bool(candidate.get("already_loaded")),
                        },
                    )
                    continue
                if key in seen:
                    skip_reasons["duplicate"] += 1
                    accepted_card = True
                    write_debug_log(
                        image_debug_log,
                        {
                            **card_log,
                            "reason": "duplicate",
                            "candidate_url": url,
                            "candidate_context_url": candidate.get("context_url") or "",
                            "candidate_title": candidate.get("title") or "",
                            "already_loaded": bool(candidate.get("already_loaded")),
                        },
                    )
                    continue
                if do_embed_validation and embed_page is not None:
                    embed_result = embed_image_loads(
                        embed_page,
                        url,
                        embed_timeout_ms,
                        embed_slow_threshold_ms,
                    )
                    if not embed_result.get("ok"):
                        skip_reasons["embed_unavailable"] += 1
                        write_debug_log(
                            image_debug_log,
                            {
                                **card_log,
                                "reason": "embed_unavailable",
                                "candidate_url": url,
                                "candidate_context_url": candidate.get("context_url") or "",
                                "candidate_title": candidate.get("title") or "",
                                "already_loaded": bool(candidate.get("already_loaded")),
                                "image_load_check": embed_result,
                            },
                        )
                        continue
                else:
                    embed_result = None
                width = candidate.get("width")
                height = candidate.get("height")
                if not width or not height:
                    width, height = parse_dimensions_from_text(candidate.get("dimension_text") or "")
                if not width or not height:
                    width, height = parse_dimensions_from_url(url)
                if not width or not height:
                    width = card.get("width")
                    height = card.get("height")
                seen.add(key)
                results.append(
                    {
                        "url": url,
                        "context_url": candidate.get("context_url") or search_url,
                        "title": candidate.get("title") or card.get("alt") or "",
                        **({"image_load_check": embed_result} if embed_result else {}),
                        **shape_info(int(width) if width else None, int(height) if height else None),
                    }
                )
                accepted = True
                accepted_card = True
                break

            if not accepted and not accepted_card:
                skip_reasons["card_without_accepted_image"] += 1
                write_debug_log(
                    image_debug_log,
                    {
                        **card_log,
                        "reason": "card_without_accepted_image",
                        "candidate_count": len(candidates),
                    },
                )

            if len(results) < max_images:
                close_google_image_viewer(page)

            if len(results) >= max_images:
                break

        context.close()
        if browser:
            browser.close()

    elapsed = time.perf_counter() - started_at
    print(
        f"[image-search] {query}: target={max_images}, clicked_fallback={attempted_cards}, "
        f"results={len(results)}, elapsed={elapsed:.1f}s, skips={dict(skip_reasons)}",
        flush=True,
    )
    write_debug_log(
        image_debug_log,
        {
            "event": "image_search_summary",
            "query": query,
            "target": max_images,
            "clicked_fallback": attempted_cards,
            "results": len(results),
            "elapsed_seconds": round(elapsed, 3),
            "skips": dict(skip_reasons),
        },
    )
    return search_url, results


def search_activity_images(
    query,
    max_images,
    api_key,
    cse_id,
    source,
    headed,
    timeout,
    user_data_dir,
    browser_channel,
    manual_verification_timeout,
    image_debug_log,
    do_embed_validation,
    embed_timeout_ms,
    embed_slow_threshold_ms,
):
    if source == "google-api":
        return search_google_images_api(query, max_images, api_key, cse_id)
    if source == "playwright":
        return search_google_images_playwright(
            query,
            max_images,
            headed=headed,
            timeout=timeout,
            user_data_dir=user_data_dir,
            browser_channel=browser_channel,
            manual_verification_timeout=manual_verification_timeout,
            image_debug_log=image_debug_log,
            do_embed_validation=do_embed_validation,
            embed_timeout_ms=embed_timeout_ms,
            embed_slow_threshold_ms=embed_slow_threshold_ms,
        )
    if api_key and cse_id:
        return search_google_images_api(query, max_images, api_key, cse_id)
    return search_google_images_playwright(
        query,
        max_images,
        headed=headed,
        timeout=timeout,
        user_data_dir=user_data_dir,
        browser_channel=browser_channel,
        manual_verification_timeout=manual_verification_timeout,
        image_debug_log=image_debug_log,
        do_embed_validation=do_embed_validation,
        embed_timeout_ms=embed_timeout_ms,
        embed_slow_threshold_ms=embed_slow_threshold_ms,
    )


def search_google_images_page(query, max_images):
    url = google_search_url(query)
    response = requests.get(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0 Safari/537.36"
            ),
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        },
        timeout=25,
    )
    response.raise_for_status()
    return url, parse_google_images(response.text, max_images)


def request_headers():
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }


def choose_store_result(game_name, results):
    if not results:
        return None
    target = normalize_name(game_name)
    exact = [item for item in results if normalize_name(item.get("trackName") or item.get("title")) == target]
    if exact:
        return exact[0]
    contains = [
        item
        for item in results
        if target and (target in normalize_name(item.get("trackName") or item.get("title")) or normalize_name(item.get("trackName") or item.get("title")) in target)
    ]
    return contains[0] if contains else results[0]


def search_apple_store_images(game_name, max_images):
    response = requests.get(
        APPLE_STORE_SEARCH_API,
        params={"term": game_name, "country": "us", "entity": "software", "media": "software", "limit": 5},
        headers=request_headers(),
        timeout=25,
    )
    response.raise_for_status()
    payload = response.json()
    result = choose_store_result(game_name, payload.get("results") or [])
    if not result:
        return None, []

    app_url = result.get("trackViewUrl")
    images = []
    seen = set()
    for url in (result.get("screenshotUrls") or []) + (result.get("ipadScreenshotUrls") or []):
        if not url or url in seen:
            continue
        seen.add(url)
        width, height = parse_dimensions_from_url(url)
        images.append(
            {
                "url": url,
                "source_url": app_url,
                "title": result.get("trackName") or game_name,
                "store": "apple_app_store",
                **shape_info(width, height),
            }
        )
        if len(images) >= max_images:
            break
    return app_url, images


def google_play_app_id_from_search(html):
    match = re.search(r"/store/apps/details\?id=([A-Za-z0-9._]+)", html)
    return match.group(1) if match else None


def parse_google_play_images(html, max_images):
    by_base_url = {}
    for raw_url in re.findall(r"https://play-lh\.googleusercontent\.com/[^\"\\]+", html):
        url = raw_url.replace("\\u003d", "=").replace("\\u0026", "&")
        url = url.split('"')[0]
        base_url = re.sub(r"=w\d{2,5}-h\d{2,5}.*$", "", url)
        width, height = parse_dimensions_from_url(url)
        if not width or not height or width < 200 or height < 200:
            continue
        existing = by_base_url.get(base_url)
        if existing and (existing["width"] or not width):
            continue
        by_base_url[base_url] = {"url": url, **shape_info(width, height)}
        if len(by_base_url) >= max_images and all(item["width"] for item in by_base_url.values()):
            break
    return list(by_base_url.values())[:max_images]


def search_google_play_images(game_name, max_images):
    search_response = requests.get(
        GOOGLE_PLAY_SEARCH,
        params={"q": game_name, "c": "apps", "hl": "en_US", "gl": "US"},
        headers=request_headers(),
        timeout=25,
    )
    search_response.raise_for_status()
    app_id = google_play_app_id_from_search(search_response.text)
    if not app_id:
        return None, []

    details_response = requests.get(
        GOOGLE_PLAY_DETAILS,
        params={"id": app_id, "hl": "en_US", "gl": "US"},
        headers=request_headers(),
        timeout=25,
    )
    details_response.raise_for_status()
    app_url = f"{GOOGLE_PLAY_DETAILS}?id={app_id}&hl=en_US&gl=US"
    images = []
    for item in parse_google_play_images(details_response.text, max_images):
        images.append(
            {
                **item,
                "source_url": app_url,
                "title": game_name,
                "store": "google_play",
            }
        )
    return app_url, images


def search_store_images(game_name, max_images, store_source):
    if store_source in ("auto", "apple"):
        app_url, images = search_apple_store_images(game_name, max_images)
        if images or store_source == "apple":
            return app_url, images
    return search_google_play_images(game_name, max_images)


def has_store_supplement(game):
    return any(
        isinstance(item, dict) and image_method(item) == STORE_SUPPLEMENT_METHOD
        for item in game.get("screenshot_or_visual_references") or []
    )


def remove_store_supplements(game):
    refs = game.get("screenshot_or_visual_references") or []
    kept = [item for item in refs if not (isinstance(item, dict) and image_method(item) == STORE_SUPPLEMENT_METHOD)]
    removed = len(refs) - len(kept)
    game["screenshot_or_visual_references"] = kept
    return removed


def supplement_store_images(game, max_images, store_source, refresh_existing):
    if refresh_existing:
        remove_store_supplements(game)
    elif has_store_supplement(game):
        return 0

    app_url, images = search_store_images(game["name"], max_images, store_source)
    now = datetime.now(timezone.utc).isoformat()
    refs = game.setdefault("screenshot_or_visual_references", [])
    for index, image in enumerate(images[:max_images], start=1):
        refs.append(
            {
                "url": image["url"],
                "description": f"US store screenshot {index}: {image.get('title') or game['name']}",
                "source_url": image.get("source_url") or app_url,
                "collection_method": STORE_SUPPLEMENT_METHOD,
                "image_source_type": "bulk_store_supplement",
                "store_source": image.get("store"),
                "store_country": "US",
                "width": image["width"],
                "height": image["height"],
                "aspect_ratio": image["aspect_ratio"],
                "orientation": image["orientation"],
                "collected_at": now,
            }
        )
    return len(images[:max_images])


def supplement_activity(
    game,
    activity,
    max_images,
    api_key,
    cse_id,
    source,
    headed,
    timeout,
    user_data_dir,
    browser_channel,
    manual_verification_timeout,
    image_debug_log,
    refresh_existing_supplement,
    embed_page,
    embed_timeout_ms,
    embed_slow_threshold_ms,
    activity_image_budget_seconds,
    skip_embed_validation,
):
    query = activity_query(game["name"], activity)
    original_images = list(activity.get("images") or [])
    manual_images = [
        image
        for image in original_images
        if isinstance(image, dict) and not is_activity_supplement_image(image)
    ]
    existing_supplement_images = [] if refresh_existing_supplement else valid_activity_supplement_images(activity)[:max_images]
    missing_images = max_images - len(existing_supplement_images)
    if missing_images <= 0:
        activity["images"] = manual_images + existing_supplement_images[:max_images]
        return max_images
    actual_source = source
    if source == "auto":
        actual_source = "google-api" if api_key and cse_id else "playwright"
    started_at = time.perf_counter()
    now = datetime.now(timezone.utc).isoformat()
    deduped_supplement_images = []
    seen = {dedupe_key(image.get("url")) for image in manual_images + existing_supplement_images if image.get("url")}
    attempted_candidate_keys = set()
    search_url = google_search_url(query)
    batch_round = 0
    while len(deduped_supplement_images) < missing_images and (time.perf_counter() - started_at) < activity_image_budget_seconds:
        batch_round += 1
        target_candidates = batch_round * EMBED_CHECK_BATCH_SIZE
        search_limit = target_candidates if actual_source == "playwright" else max(target_candidates * 3, target_candidates + len(manual_images))
        search_url, images = search_activity_images(
            query,
            search_limit,
            api_key,
            cse_id,
            source,
            headed,
            timeout,
            user_data_dir,
            browser_channel,
            manual_verification_timeout,
            image_debug_log,
            actual_source == "playwright" and not skip_embed_validation,
            embed_timeout_ms,
            embed_slow_threshold_ms,
        )
        supplement_images = [
            {
                "url": image["url"],
                "caption": image.get("title") or f"Google 图片搜索补充：{query}",
                "source_url": image.get("context_url") or search_url,
                "google_image_search_url": search_url,
                "collection_method": SUPPLEMENT_METHOD,
                "image_source_type": "bulk_supplement",
                "automation_method": "playwright_browser" if actual_source == "playwright" else "google_custom_search_api",
                "search_query": query,
                "width": image["width"],
                "height": image["height"],
                "aspect_ratio": image["aspect_ratio"],
                "orientation": image["orientation"],
                "collected_at": now,
                **({"image_load_check": image["image_load_check"]} if image.get("image_load_check") else {}),
            }
            for image in images
            if is_standard_image_url(image.get("url"), allow_no_ext=True)
        ]
        new_candidates = []
        for image in supplement_images:
            key = dedupe_key(image["url"])
            if key in seen or key in attempted_candidate_keys:
                continue
            attempted_candidate_keys.add(key)
            new_candidates.append(image)

        for image in new_candidates:
            embed_result = None
            if not skip_embed_validation and actual_source == "playwright":
                embed_result = image.get("image_load_check")
                if not embed_result or not embed_result.get("ok"):
                    write_debug_log(
                        image_debug_log,
                        {
                            "event": "image_candidate_skip",
                            "query": query,
                            "reason": "missing_or_failed_embed_validation",
                            "candidate_url": image["url"],
                            "candidate_context_url": image.get("source_url") or "",
                            "candidate_title": image.get("caption") or "",
                            **({"image_load_check": embed_result} if embed_result else {}),
                        },
                    )
                    continue
                apply_embed_load_metadata(image, embed_result)
            elif not skip_embed_validation and embed_page is not None:
                embed_result = embed_image_loads(embed_page, image["url"], embed_timeout_ms, embed_slow_threshold_ms)
                if not embed_result.get("ok"):
                    write_debug_log(
                        image_debug_log,
                        {
                            "event": "image_candidate_skip",
                            "query": query,
                            "reason": "embed_unavailable",
                            "candidate_url": image["url"],
                            "candidate_context_url": image.get("source_url") or "",
                            "candidate_title": image.get("caption") or "",
                            "image_load_check": embed_result,
                        },
                    )
                    continue
                apply_embed_load_metadata(image, embed_result)
            elif image.get("image_load_check"):
                apply_embed_load_metadata(image, image["image_load_check"])

            key = dedupe_key(image["url"])
            seen.add(key)
            deduped_supplement_images.append(image)
            if embed_result and embed_result.get("long_load"):
                write_debug_log(
                    image_debug_log,
                    {
                        "event": "image_candidate_mark",
                        "query": query,
                        "reason": "long_load",
                        "candidate_url": image["url"],
                        "candidate_context_url": image.get("source_url") or "",
                        "candidate_title": image.get("caption") or "",
                        "image_load_check": embed_result,
                    },
                )
            if len(deduped_supplement_images) >= missing_images:
                break
    final_supplement_images = existing_supplement_images + deduped_supplement_images
    activity["images"] = manual_images + final_supplement_images
    if len(final_supplement_images) < max_images:
        elapsed = time.perf_counter() - started_at
        print(
            f"[timing] {query}: rounds={batch_round}, kept={len(existing_supplement_images)}, "
            f"wrote={len(deduped_supplement_images)}, needed={max_images}, elapsed={elapsed:.1f}s",
            flush=True,
        )
        return len(final_supplement_images)
    elapsed = time.perf_counter() - started_at
    print(
        f"[timing] {query}: rounds={batch_round}, kept={len(existing_supplement_images)}, "
        f"wrote={len(deduped_supplement_images)}, needed={max_images}, elapsed={elapsed:.1f}s",
        flush=True,
    )
    return len(final_supplement_images)


def iter_json_files(input_dir, ranks):
    rank_set = set(ranks or [])
    for path in sorted(input_dir.glob("*.json")):
        payload = load_json(path)
        if rank_set and int(payload.get("rank", -1)) not in rank_set:
            continue
        yield path, payload


def set_supplement_meta(payload):
    payload["manual_image_supplement"] = {
        "activity_method": SUPPLEMENT_METHOD,
        "store_method": STORE_SUPPLEMENT_METHOD,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "note": "Activity images are filled from Google Custom Search when credentials are supplied, otherwise from Google Images via Playwright browser automation. Game-level store screenshots are filled from US Apple App Store first, then US Google Play when --store-source=auto. Existing manual images and visual references are marked as original_manual_json.",
    }


def main():
    args = parse_args()
    image_debug_log = None if args.no_image_debug_log else args.image_debug_log
    updated_files = 0
    updated_activities = 0
    updated_store_games = 0
    warnings = []
    embed_page = None
    embed_browser = None
    embed_context = None
    embed_playwright = None

    needs_external_embed_validation = (
        not args.skip_embed_validation
        and not args.dry_run
        and not args.skip_activity_images
        and (
            args.activity_image_source == "google-api"
            or (args.activity_image_source == "auto" and args.google_api_key and args.google_cse_id)
        )
    )

    if needs_external_embed_validation:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as error:
            raise RuntimeError("缺少 playwright。请先运行：pip install playwright && python -m playwright install chromium") from error
        embed_playwright = sync_playwright().start()
        launch_options = {"headless": not args.headed}
        if args.browser_channel:
            launch_options["channel"] = args.browser_channel
        embed_browser = embed_playwright.chromium.launch(**launch_options)
        embed_context = embed_browser.new_context(extra_http_headers={"Referer": args.embed_referer})
        embed_page = embed_context.new_page()
        embed_page.goto("data:text/html,<html><body></body></html>", wait_until="domcontentloaded")

    try:
        for path, payload in iter_json_files(args.input_dir, args.rank):
            file_touched = False
            game_updates = 0
            if mark_existing_visual_references(payload) and not args.dry_run:
                set_supplement_meta(payload)
                write_json(path, payload)
                file_touched = True

            if not args.skip_store_images and (args.refresh_existing_supplement or not has_store_supplement(payload)):
                print(f"[plan-store] #{payload.get('rank')} {payload.get('name')} -> US {args.store_source} store screenshots", flush=True)
                if args.dry_run:
                    updated_store_games += 1
                else:
                    try:
                        count = supplement_store_images(payload, args.max_images, args.store_source, args.refresh_existing_supplement)
                        if count:
                            print(f"[ok-store] {path.name}: wrote {count} store screenshots", flush=True)
                            set_supplement_meta(payload)
                            write_json(path, payload)
                            file_touched = True
                            updated_store_games += 1
                            time.sleep(args.delay)
                        else:
                            warnings.append(f"{path.name}: no US store screenshots for {payload.get('name')}")
                    except Exception as error:
                        warnings.append(f"{path.name}: store screenshots for {payload.get('name')}: {error}")

            if not args.skip_activity_images:
                for activity in payload.get("activity_types") or []:
                    if mark_existing_images(activity) and not args.dry_run:
                        set_supplement_meta(payload)
                        write_json(path, payload)
                        file_touched = True
                    if prune_invalid_activity_supplement_images(activity) and not args.dry_run:
                        set_supplement_meta(payload)
                        write_json(path, payload)
                        file_touched = True
                    if not should_supplement(activity, args.refresh_existing_supplement, args.max_images):
                        continue

                    query = activity_query(payload["name"], activity)
                    print(f"[plan] #{payload.get('rank')} {payload.get('name')} / {activity.get('display_name') or activity.get('type')} -> {query}", flush=True)
                    if args.dry_run:
                        game_updates += 1
                        continue

                    try:
                        count = supplement_activity(
                            payload,
                            activity,
                            args.max_images,
                            args.google_api_key,
                            args.google_cse_id,
                            args.activity_image_source,
                            args.headed,
                            args.browser_timeout,
                            args.browser_user_data_dir,
                            args.browser_channel,
                            args.manual_verification_timeout,
                            image_debug_log,
                            args.refresh_existing_supplement,
                            embed_page,
                            args.embed_timeout_ms,
                            args.embed_slow_threshold_ms,
                            args.activity_image_budget_seconds,
                            args.skip_embed_validation,
                        )
                        if count:
                            status = "ok" if count == args.max_images else "partial"
                            print(f"[{status}] {path.name}: kept/wrote {count} automatic images", flush=True)
                            set_supplement_meta(payload)
                            write_json(path, payload)
                            file_touched = True
                            if count == args.max_images:
                                game_updates += 1
                            time.sleep(args.delay)
                        if count < args.max_images:
                            warnings.append(f"{path.name}: fewer than {args.max_images} clean automatic images for {query}")
                    except Exception as error:
                        warnings.append(f"{path.name}: {query}: {error}")

            if file_touched:
                updated_files += 1
            updated_activities += game_updates
    finally:
        if embed_context:
            embed_context.close()
        if embed_browser:
            embed_browser.close()
        if embed_playwright:
            embed_playwright.stop()

    print(
        f"done: files_updated={updated_files}, activities_touched={updated_activities}, "
        f"store_games_touched={updated_store_games}, warnings={len(warnings)}"
    )
    for warning in warnings:
        print(f"[warning] {warning}")


if __name__ == "__main__":
    main()
