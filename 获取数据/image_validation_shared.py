import hashlib
import re
from datetime import datetime, timezone
from urllib.parse import urlparse


IMAGE_EXT_RE = re.compile(r"\.(?:png|jpe?g|webp|gif)(?:[?#].*)?$", re.I)
NON_IMAGE_EXT_RE = re.compile(r"\.(?:css|js|mjs|json|html?|xml|svg|ico|woff2?|ttf|otf)(?:[?#].*)?$", re.I)
DATA_IMAGE_RE = re.compile(r"^data:image/(?:png|jpe?g|webp|gif);base64,", re.I)
NOISE_HOST_RE = re.compile(
    r"(?:schema\.org|facebook\.com|lookaside\.fbsbx\.com|lookaside\.instagram\.com|doubleclick|googletagmanager)",
    re.I,
)
NOISE_URL_RE = re.compile(
    r"(?:favicon|logo|sprite|avatar|pixel|tracking|blank|placeholder|1x1\.gif|"
    r"apps\.apple\.com/assets|supports-|/tr(?:[?#]|$)|google\.com/logos)",
    re.I,
)


def is_google_thumbnail_url(url):
    if DATA_IMAGE_RE.match(url or ""):
        return True
    parsed = urlparse(url or "")
    host = parsed.netloc.lower()
    path = parsed.path or ""
    return (
        "encrypted-tbn" in host
        or (host.endswith("gstatic.com") and path.startswith("/images"))
        or "favicon" in path.lower()
    )


def is_standard_image_url(url, allow_no_ext=False):
    if not url or not isinstance(url, str) or not url.startswith(("http://", "https://")):
        return False
    if is_google_thumbnail_url(url):
        return False
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path or ""
    if not host or NOISE_HOST_RE.search(host) or NOISE_URL_RE.search(url):
        return False
    if NON_IMAGE_EXT_RE.search(path):
        return False
    if allow_no_ext:
        return bool(IMAGE_EXT_RE.search(path) or not re.search(r"\.[A-Za-z0-9]{2,5}$", path))
    return bool(IMAGE_EXT_RE.search(path))


def image_key(url):
    if DATA_IMAGE_RE.match(url or ""):
        return f"data:{hashlib.sha256(url.encode('utf-8')).hexdigest()}"
    parsed = urlparse(url or "")
    host = parsed.netloc.lower()
    path = parsed.path.rstrip("/")
    if "encrypted-tbn" in host or path.endswith("/images"):
        return f"{host}{path}?{parsed.query}"
    return f"{host}{path}"


def embed_image_loads(page, url, timeout_ms, slow_threshold_ms):
    responses = []
    failures = []

    def remember_response(response):
        if response.request.resource_type == "image":
            responses.append(
                {
                    "url": response.url,
                    "status": response.status,
                    "content_type": (response.headers.get("content-type") or "").lower(),
                }
            )

    def remember_failure(request):
        if request.resource_type == "image":
            failures.append(
                {
                    "url": request.url,
                    "failure": request.failure,
                }
            )

    page.on("response", remember_response)
    page.on("requestfailed", remember_failure)
    try:
        result = page.evaluate(
            """
            async ({ url, timeoutMs }) => {
              document.body.innerHTML = "";
              const img = new Image();
              img.decoding = "async";
              img.loading = "eager";
              const startedAt = performance.now();
              return await new Promise((resolve) => {
                let done = false;
                const finish = (payload) => {
                  if (done) return;
                  done = true;
                  clearTimeout(timer);
                  resolve({
                    ...payload,
                    load_time_ms: Math.round(performance.now() - startedAt),
                  });
                };
                const timer = window.setTimeout(() => {
                  img.src = "";
                  finish({ ok: false, event: "timeout" });
                }, timeoutMs);
                img.onload = () =>
                  finish({
                    ok: true,
                    event: "load",
                    natural_width: img.naturalWidth || 0,
                    natural_height: img.naturalHeight || 0,
                    current_src: img.currentSrc || img.src || "",
                  });
                img.onerror = () =>
                  finish({
                    ok: false,
                    event: "error",
                    natural_width: img.naturalWidth || 0,
                    natural_height: img.naturalHeight || 0,
                    current_src: img.currentSrc || img.src || "",
                  });
                document.body.appendChild(img);
                img.src = url;
              });
            }
            """,
            {"url": url, "timeoutMs": timeout_ms},
        )
    finally:
        page.remove_listener("response", remember_response)
        page.remove_listener("requestfailed", remember_failure)

    image_response = responses[-1] if responses else {}
    failed_request = failures[-1] if failures else {}
    ok = (
        bool(result.get("ok"))
        and not failed_request
        and image_response.get("status", 200) < 400
        and (result.get("natural_width") or 0) > 0
        and (result.get("natural_height") or 0) > 0
    )
    return {
        "ok": ok,
        "method": "playwright_embed_check",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "load_time_ms": result.get("load_time_ms"),
        "long_load": (result.get("load_time_ms") or 0) > slow_threshold_ms,
        "http_status": image_response.get("status"),
        "content_type": image_response.get("content_type"),
        "event": result.get("event"),
        "current_src": result.get("current_src") or image_response.get("url") or url,
        "natural_width": result.get("natural_width"),
        "natural_height": result.get("natural_height"),
        "failure": failed_request.get("failure"),
    }


def apply_embed_load_metadata(image, result):
    image["image_load_check"] = {
        "method": result.get("method") or "playwright_embed_check",
        "checked_at": result.get("checked_at") or datetime.now(timezone.utc).isoformat(),
        "load_time_ms": result.get("load_time_ms"),
        "long_load": bool(result.get("long_load")),
        "http_status": result.get("http_status"),
        "event": result.get("event"),
        "natural_width": result.get("natural_width"),
        "natural_height": result.get("natural_height"),
    }
    if result.get("content_type"):
        image["image_load_check"]["content_type"] = result["content_type"]
    if result.get("current_src"):
        image["image_load_check"]["current_src"] = result["current_src"]
    if result.get("failure"):
        image["image_load_check"]["failure"] = result["failure"]
