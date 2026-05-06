from __future__ import annotations

import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup, Tag


BASE_URL = "https://monopolygo.wiki"
EVENTS_URL = f"{BASE_URL}/tag/events/"
LISTING_URL = f"{BASE_URL}/page/2/"
ALBUMS_URL = f"{BASE_URL}/tag/albums/"
SUPPLEMENTAL_SOURCE_URLS = (ALBUMS_URL,)
SUPPLEMENTAL_SOURCE_PAGES = 2
SOURCE_NAME = "monopolygo.wiki"
COMPETITOR_NAME = "monopoly_go"
BUFF_MAX_DURATION_SECONDS = 12 * 60 * 60
MONTH_PATTERN = (
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
)
ALBUM_DATE_TEXT_PATTERN = (
    rf"{MONTH_PATTERN}\.?\s+\d{{1,2}}(?:st|nd|rd|th)?"
    r"(?:,\s*20\d{2})?"
    r"(?:\s+at\s+\d{1,2}(?::\d{2})?\s*(?:AM|PM)?\s*[A-Z]{2,4})?"
)
TRACK_DEFINITIONS = (
    {"id": "one_time", "label": "一次性活动", "sort": 10},
    {"id": "buff", "label": "buff", "sort": 20},
    {"id": "album", "label": "album", "sort": 30},
    {"id": "tycoon_class", "label": "Tycoon-class", "sort": 40},
    {"id": "tournaments", "label": "其它 tournaments", "sort": 50},
    {"id": "minigames", "label": "minigames", "sort": 60},
)
TRACK_DEFINITION_BY_ID = {track["id"]: track for track in TRACK_DEFINITIONS}
LIFECYCLE_DEFINITIONS = (
    {"id": "one_time", "label": "一次性", "sort": 10},
    {"id": "recurring", "label": "周期性", "sort": 20},
    {"id": "irregular", "label": "不定期", "sort": 30},
    {"id": "seasonal", "label": "赛季性", "sort": 40},
)
LIFECYCLE_DEFINITION_BY_ID = {lifecycle["id"]: lifecycle for lifecycle in LIFECYCLE_DEFINITIONS}
TRACK_GROUP_LIFECYCLES = {
    "one_time": "one_time",
    "buff": "recurring",
    "album": "seasonal",
    "tycoon_class": "recurring",
    "tournaments": "recurring",
    "minigames": "irregular",
}
ONE_TIME_EVENT_NAMES = {
    "trade fest",
    "lucky coin",
}
EXPLICIT_BUFF_NAME_PREFIXES = (
    "goldenblitz",
    "highroller",
    "luckychance",
)


@dataclass(frozen=True)
class PostLink:
    url: str
    title: str
    published_date: str | None
    excerpt: str | None = None


class MonopolyGoWikiCollector:
    """Collect scheduled Monopoly GO events from monopolygo.wiki."""

    def __init__(self, timeout: int = 30, request_delay: float = 0.5) -> None:
        self.timeout = timeout
        self.request_delay = request_delay
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            }
        )

    def collect(
        self,
        pages: int = 1,
        max_posts: int | None = None,
        source_url: str = LISTING_URL,
        supplemental_source_urls: tuple[str, ...] = SUPPLEMENTAL_SOURCE_URLS,
        supplemental_source_pages: int = SUPPLEMENTAL_SOURCE_PAGES,
    ) -> dict[str, Any]:
        posts = self.discover_posts(pages=pages, source_url=source_url)
        for supplemental_url in supplemental_source_urls:
            posts.extend(self.discover_posts(pages=supplemental_source_pages, source_url=supplemental_url))
        posts = dedupe_posts(posts)
        if max_posts is not None:
            posts = posts[:max_posts]

        events: list[dict[str, Any]] = []
        articles: list[dict[str, Any]] = []
        seen_keys: set[tuple[str, str, int, int]] = set()
        seen_article_urls: set[str] = set()

        for index, post in enumerate(posts):
            if index:
                time.sleep(self.request_delay)

            result = self.parse_post(post)
            article = result["article"]
            if article["url"] not in seen_article_urls:
                seen_article_urls.add(article["url"])
                articles.append(article)

            for event in result["events"]:
                key = (
                    event["source_url"],
                    event["name"],
                    event["start_timestamp"],
                    event["end_timestamp"],
                )
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                events.append(event)

        for event in build_album_events(articles):
            key = (
                event["source_url"],
                event["name"],
                event["start_timestamp"],
                event["end_timestamp"],
            )
            if key in seen_keys:
                continue
            seen_keys.add(key)
            events.append(event)

        events = merge_named_minigames(events)
        self.enrich_events_with_related_articles(events, articles)
        tracks = assign_event_tracks(events)
        events.sort(key=lambda item: (item["start_timestamp"], item["name"]))
        return {
            "schema_version": "1.0",
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "competitor": COMPETITOR_NAME,
            "source": SOURCE_NAME,
            "listing_source_url": source_url,
            "supplemental_source_urls": list(supplemental_source_urls),
            "lifecycles": list(LIFECYCLE_DEFINITIONS),
            "tracks": tracks,
            "articles": articles,
            "events": events,
        }

    def discover_posts(self, pages: int = 1, source_url: str = LISTING_URL) -> list[PostLink]:
        posts: list[PostLink] = []
        seen_urls: set[str] = set()

        for page_index in range(pages):
            url = build_listing_url(source_url, page_index)
            html = self.fetch(url)
            soup = BeautifulSoup(html, "html.parser")

            for article in soup.select("article.gh-card, article"):
                link = article.select_one("a.gh-card-link[href]")
                if not link:
                    link = article.select_one("a[href]")
                if not link:
                    continue

                post_url = urljoin(BASE_URL, link["href"])
                if not is_collectable_post_url(post_url) or post_url in seen_urls:
                    continue

                title_tag = article.select_one(".gh-card-title")
                excerpt_tag = article.select_one(".gh-card-excerpt, .gh-card-content, p")
                time_tag = article.select_one("time[datetime]")
                posts.append(
                    PostLink(
                        url=post_url,
                        title=clean_text(title_tag.get_text(" ", strip=True)) if title_tag else "",
                        published_date=time_tag.get("datetime") if time_tag else None,
                        excerpt=clean_text(excerpt_tag.get_text(" ", strip=True)) if excerpt_tag else None,
                    )
                )
                seen_urls.add(post_url)

            if posts:
                continue

            for link in soup.select("a[href]"):
                post_url = urljoin(BASE_URL, link["href"])
                if not is_collectable_post_url(post_url) or post_url in seen_urls:
                    continue

                title = clean_text(link.get_text(" ", strip=True))
                if not title:
                    continue
                posts.append(PostLink(url=post_url, title=title, published_date=None))
                seen_urls.add(post_url)

        return posts

    def parse_post(self, post: PostLink) -> dict[str, Any]:
        html = self.fetch(post.url)
        return self.parse_post_html(post=post, html=html)

    def parse_post_html(self, post: PostLink, html: str) -> dict[str, Any]:
        soup = BeautifulSoup(html, "html.parser")

        title_tag = soup.select_one(".gh-article-title")
        post_title = clean_text(title_tag.get_text(" ", strip=True)) if title_tag else post.title
        published_tag = soup.select_one(".gh-article-meta-date[datetime]")
        published_date = published_tag.get("datetime") if published_tag else post.published_date
        content = soup.select_one("section.gh-content") or soup
        article = build_article_record(
            post=post,
            title=post_title,
            published_date=published_date,
            content=content,
            soup=soup,
        )

        events: list[dict[str, Any]] = []
        current_category: str | None = None

        for node in content.find_all(["h4", "div"]):
            if node.name == "h4":
                current_category = clean_text(node.get_text(" ", strip=True))
                continue

            if not isinstance(node, Tag) or "event-block" not in node.get("class", []):
                continue

            parsed = self.parse_event_block(
                block=node,
                category=current_category or "Unknown",
                post=post,
                post_title=post_title,
                published_date=published_date,
                article=article,
            )
            if parsed:
                events.append(parsed)

        if not events:
            article_event = self.parse_article_event(post=post, article=article, content=content)
            if article_event:
                events.append(article_event)

        return {"article": article, "events": events}

    def parse_event_block(
        self,
        block: Tag,
        category: str,
        post: PostLink,
        post_title: str,
        published_date: str | None,
        article: dict[str, Any],
    ) -> dict[str, Any] | None:
        time_spans = block.select(".local-date[data-date]")
        if len(time_spans) < 2:
            return None

        start_timestamp = parse_timestamp(time_spans[0].get("data-date"))
        end_timestamp = parse_timestamp(time_spans[1].get("data-date"))
        if start_timestamp is None or end_timestamp is None:
            return None

        name = extract_event_name(block)
        if not name:
            return None

        link = block.select_one("a.event-link-title[href]")
        image = block.select_one("img")
        duration = extract_duration(block)
        classes = block.get("class", [])
        article_summary = article.get("summary")

        return {
            "id": build_event_id(name, start_timestamp, end_timestamp),
            "competitor": COMPETITOR_NAME,
            "source": SOURCE_NAME,
            "source_url": post.url,
            "source_post_title": post_title,
            "source_published_date": published_date,
            "category": category,
            "name": name,
            "start_time": timestamp_to_iso(start_timestamp),
            "end_time": timestamp_to_iso(end_timestamp),
            "timezone": "UTC",
            "start_timestamp": start_timestamp,
            "end_timestamp": end_timestamp,
            "duration_seconds": max(0, end_timestamp - start_timestamp),
            "duration_text": duration,
            "detail_url": urljoin(BASE_URL, link["href"]) if link else None,
            "image_url": urljoin(BASE_URL, image["src"]) if image and image.get("src") else None,
            "description": article_summary,
            "article_summary": article_summary,
            "related_article": compact_article_reference(article),
            "raw": {
                "display_start": clean_text(time_spans[0].get_text(" ", strip=True)),
                "display_end": clean_text(time_spans[1].get_text(" ", strip=True)),
                "classes": classes,
            },
        }

    def parse_article_event(
        self,
        post: PostLink,
        article: dict[str, Any],
        content: Tag,
    ) -> dict[str, Any] | None:
        if article["type"] in {"album", "reward_links", "general"}:
            return None

        time_spans = content.select(".local-date[data-date]")
        if len(time_spans) < 2:
            return None

        start_timestamp = parse_timestamp(time_spans[0].get("data-date"))
        end_timestamp = parse_timestamp(time_spans[1].get("data-date"))
        if start_timestamp is None or end_timestamp is None:
            return None

        name = clean_event_title(article["title"])
        if not name:
            return None

        category = article_type_to_category(article["type"])
        image = content.select_one("img")
        summary = article.get("summary")
        return {
            "id": build_event_id(name, start_timestamp, end_timestamp),
            "competitor": COMPETITOR_NAME,
            "source": SOURCE_NAME,
            "source_url": post.url,
            "source_post_title": article["title"],
            "source_published_date": article.get("published_date"),
            "category": category,
            "name": name,
            "start_time": timestamp_to_iso(start_timestamp),
            "end_time": timestamp_to_iso(end_timestamp),
            "timezone": "UTC",
            "start_timestamp": start_timestamp,
            "end_timestamp": end_timestamp,
            "duration_seconds": max(0, end_timestamp - start_timestamp),
            "duration_text": None,
            "detail_url": post.url,
            "image_url": urljoin(BASE_URL, image["src"]) if image and image.get("src") else None,
            "description": summary,
            "article_summary": summary,
            "related_article": compact_article_reference(article),
            "raw": {
                "display_start": clean_text(time_spans[0].get_text(" ", strip=True)),
                "display_end": clean_text(time_spans[1].get_text(" ", strip=True)),
                "classes": [],
            },
        }

    def enrich_events_with_related_articles(
        self,
        events: list[dict[str, Any]],
        articles: list[dict[str, Any]],
    ) -> None:
        related_articles = [article for article in articles if article["type"] != "daily_events"]
        for event in events:
            event_name = normalize_match_text(event["name"])
            matches = [
                article
                for article in related_articles
                if event_name
                and (
                    event_name in normalize_match_text(article["title"])
                    or normalize_match_text(clean_event_title(article["title"])) in event_name
                )
            ]
            if not matches:
                continue

            event["related_articles"] = [compact_article_reference(article) for article in matches[:3]]
            if not event.get("description"):
                event["description"] = matches[0].get("summary")

    def fetch(self, url: str) -> str:
        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()
        return response.text


def parse_timestamp(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def timestamp_to_iso(timestamp: int) -> str:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat(timespec="seconds")


def build_listing_url(source_url: str, page_index: int) -> str:
    if page_index == 0:
        return source_url

    parsed = urlparse(source_url)
    path = parsed.path.rstrip("/")
    match = re.search(r"/page/(\d+)$", path)
    if match:
        page = int(match.group(1)) + page_index
        base_path = path[: match.start()]
        return urljoin(BASE_URL, f"{base_path}/page/{page}/")

    if path.startswith("/tag/"):
        return urljoin(source_url.rstrip("/") + "/", f"page/{page_index + 1}/")

    return urljoin(BASE_URL, f"/page/{page_index + 1}/")


def is_collectable_post_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.netloc and parsed.netloc != urlparse(BASE_URL).netloc:
        return False

    path = parsed.path.rstrip("/")
    if not path or path in {"/page/2"}:
        return False

    blocked_prefixes = (
        "/author/",
        "/tag/",
        "/page/",
        "/share/",
        "/mogo-tools/",
        "/cdn-cgi/",
    )
    return not any(path.startswith(prefix) for prefix in blocked_prefixes)


def dedupe_posts(posts: list[PostLink]) -> list[PostLink]:
    deduped: list[PostLink] = []
    seen_urls: set[str] = set()
    for post in posts:
        if post.url in seen_urls:
            continue
        seen_urls.add(post.url)
        deduped.append(post)
    return deduped


def build_album_events(articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, int, int]] = set()
    candidates = build_album_candidates(articles)
    infer_album_candidate_dates(candidates)

    for candidate in candidates:
        article = candidate["article"]
        album = candidate["album"]
        start_timestamp = candidate["start_timestamp"]
        end_timestamp = candidate["end_timestamp"]
        if start_timestamp is None or end_timestamp is None:
            continue
        if end_timestamp <= start_timestamp:
            end_timestamp = parse_album_date_text(album.get("run_end_text"), article.get("published_date"), True, year_offset=1)
            if end_timestamp is None:
                continue

        name = album.get("name") or clean_event_title(article["title"])
        key = (normalize_match_text(name), start_timestamp, end_timestamp)
        if key in seen_keys:
            continue
        seen_keys.add(key)

        events.append(
            {
                "id": build_event_id(name, start_timestamp, end_timestamp),
                "competitor": COMPETITOR_NAME,
                "source": SOURCE_NAME,
                "source_url": article["url"],
                "source_post_title": article["title"],
                "source_published_date": article.get("published_date"),
                "category": "Album",
                "name": name,
                "start_time": timestamp_to_iso(start_timestamp),
                "end_time": timestamp_to_iso(end_timestamp),
                "timezone": "UTC",
                "start_timestamp": start_timestamp,
                "end_timestamp": end_timestamp,
                "duration_seconds": max(0, end_timestamp - start_timestamp),
                "duration_text": None,
                "detail_url": article["url"],
                "image_url": article.get("image_url"),
                "description": article.get("summary"),
                "article_summary": article.get("summary"),
                "related_article": compact_article_reference(article),
                "raw": {
                    "display_start": album.get("run_start_text"),
                    "display_end": album.get("run_end_text"),
                    "classes": ["album"],
                },
            }
        )

    return events


def build_album_candidates(articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for article in articles:
        album = article.get("album")
        if article.get("type") != "album" or not album:
            continue

        candidates.append(
            {
                "article": article,
                "album": album,
                "name": album.get("name") or clean_event_title(article["title"]),
                "start_timestamp": parse_album_date_text(
                    album.get("run_start_text"), article.get("published_date"), False
                ),
                "end_timestamp": parse_album_date_text(album.get("run_end_text"), article.get("published_date"), True),
                "can_infer_dates": can_infer_album_dates(article),
            }
        )
    return candidates


def infer_album_candidate_dates(candidates: list[dict[str, Any]]) -> None:
    ordered = sorted(candidates, key=album_candidate_sort_key)
    for index, candidate in enumerate(ordered):
        next_started = next(
            (
                next_candidate
                for next_candidate in ordered[index + 1 :]
                if next_candidate["start_timestamp"] is not None
                and normalize_match_text(next_candidate["name"]) != normalize_match_text(candidate["name"])
            ),
            None,
        )
        if candidate["start_timestamp"] is not None and candidate["end_timestamp"] is None and next_started:
            candidate["end_timestamp"] = utc_day_end(next_started["start_timestamp"])
            continue

        if not candidate["can_infer_dates"] or candidate["start_timestamp"] is not None:
            continue

        previous_ended = next(
            (
                previous_candidate
                for previous_candidate in reversed(ordered[:index])
                if previous_candidate["end_timestamp"] is not None
                and normalize_match_text(previous_candidate["name"]) != normalize_match_text(candidate["name"])
            ),
            None,
        )
        if previous_ended and next_started:
            candidate["start_timestamp"] = utc_day_start(previous_ended["end_timestamp"])
            candidate["end_timestamp"] = utc_day_end(next_started["start_timestamp"])


def album_candidate_sort_key(candidate: dict[str, Any]) -> tuple[int, str]:
    article = candidate["article"]
    return (
        candidate["start_timestamp"]
        or parse_published_date_timestamp(article.get("published_date"))
        or 0,
        normalize_match_text(candidate["name"]),
    )


def can_infer_album_dates(article: dict[str, Any]) -> bool:
    text = f"{article.get('title', '')} {article.get('summary', '')}".lower()
    return bool(
        re.search(
            r"\b(next|upcoming|new|brand-new|full)\b.{0,80}\balbum\b|\balbum\b.{0,80}\b(on the way|arrives|launch|starts|begins|kicks off|set to launch)\b",
            text,
            flags=re.IGNORECASE,
        )
    )


def parse_published_date_timestamp(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp())
    except ValueError:
        return None


def utc_day_start(timestamp: int) -> int:
    day = datetime.fromtimestamp(timestamp, tz=timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    return int(day.timestamp())


def utc_day_end(timestamp: int) -> int:
    day = datetime.fromtimestamp(timestamp, tz=timezone.utc).replace(hour=23, minute=59, second=59, microsecond=0)
    return int(day.timestamp())


def parse_album_date_text(
    value: str | None,
    published_date: str | None,
    end_of_day: bool,
    year_offset: int = 0,
) -> int | None:
    if not value:
        return None

    normalized = normalize_album_date_text(value)
    year = extract_year(normalized) or extract_year(published_date) or datetime.now(timezone.utc).year
    year += year_offset
    if not extract_year(normalized):
        normalized = f"{normalized} {year}"

    for pattern in ("%B %d %Y", "%b %d %Y"):
        try:
            parsed = datetime.strptime(normalized, pattern).replace(tzinfo=timezone.utc)
            if end_of_day:
                parsed = parsed.replace(hour=23, minute=59, second=59)
            return int(parsed.timestamp())
        except ValueError:
            continue
    return None


def normalize_album_date_text(value: str) -> str:
    normalized = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", value, flags=re.IGNORECASE)
    normalized = re.sub(
        r"\s+at\s+\d{1,2}(?::\d{2})?\s*(?:AM|PM)?\s*[A-Z]{2,4}\b",
        "",
        normalized,
        flags=re.IGNORECASE,
    )
    normalized = re.sub(r",\s*", " ", normalized)
    return clean_text(normalized).strip(" .,-")


def extract_year(value: str | None) -> int | None:
    if not value:
        return None
    match = re.search(r"\b(20\d{2})\b", value)
    if match:
        return int(match.group(1))
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).year
    except ValueError:
        return None


def merge_named_minigames(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merge_rules = {
        "Partner Event": "Partner Events",
        "Dig Minigame": "Dig Minigame",
    }
    events_by_time: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for event in events:
        key = (event["start_timestamp"], event["end_timestamp"])
        events_by_time.setdefault(key, []).append(event)

    remove_ids: set[int] = set()
    for same_time_events in events_by_time.values():
        for generic_name, specific_category in merge_rules.items():
            generic_event = next(
                (
                    event
                    for event in same_time_events
                    if event.get("name") == generic_name and event.get("category") == "Special Events"
                ),
                None,
            )
            if generic_event is None:
                continue

            specific_event = next(
                (
                    event
                    for event in same_time_events
                    if event.get("category") == specific_category and event.get("name") != generic_name
                ),
                None,
            )
            if specific_event is None:
                continue

            original_name = specific_event["name"]
            merged_name = f"{generic_name}（{original_name}）"
            specific_event["name"] = merged_name
            specific_event["id"] = build_event_id(
                merged_name,
                specific_event["start_timestamp"],
                specific_event["end_timestamp"],
            )
            specific_event["merged_from"] = [
                compact_event_reference(generic_event),
                {
                    **compact_event_reference(specific_event),
                    "name": original_name,
                },
            ]
            remove_ids.add(id(generic_event))

    return [event for event in events if id(event) not in remove_ids]


def compact_event_reference(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": event.get("name"),
        "category": event.get("category"),
        "source_url": event.get("source_url"),
        "source_post_title": event.get("source_post_title"),
    }


def assign_event_tracks(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    events_by_group: dict[str, list[dict[str, Any]]] = {}
    buff_name_keys = build_buff_name_keys(events)
    for event in events:
        group_id = classify_track_group(event, buff_name_keys=buff_name_keys)
        events_by_group.setdefault(group_id, []).append(event)

    tracks: list[dict[str, Any]] = []
    for group in TRACK_DEFINITIONS:
        group_events = sorted(
            events_by_group.get(group["id"], []),
            key=lambda item: (item["start_timestamp"], item["end_timestamp"], item["name"]),
        )
        lane_ends: list[int] = []
        lane_counts: list[int] = []

        for event in group_events:
            lane_index = first_non_overlapping_lane(lane_ends, event["start_timestamp"])
            if lane_index == len(lane_ends):
                lane_ends.append(event["end_timestamp"])
                lane_counts.append(0)
            else:
                lane_ends[lane_index] = event["end_timestamp"]

            lane_counts[lane_index] += 1
            lane_number = lane_index + 1
            track_label = group["label"] if lane_number == 1 else f"{group['label']}{lane_number}"
            track_id = group["id"] if lane_number == 1 else f"{group['id']}_{lane_number}"
            lifecycle = lifecycle_for_track_group(group["id"])
            event["track_group"] = group["id"]
            event["track_group_label"] = group["label"]
            event["track"] = track_id
            event["track_label"] = track_label
            event["track_index"] = lane_number
            event["track_sort"] = group["sort"] * 100 + lane_number
            event["lifecycle"] = lifecycle["id"]
            event["lifecycle_label"] = lifecycle["label"]
            event["lifecycle_sort"] = lifecycle["sort"]

        for lane_index, count in enumerate(lane_counts):
            lane_number = lane_index + 1
            lifecycle = lifecycle_for_track_group(group["id"])
            tracks.append(
                {
                    "id": group["id"] if lane_number == 1 else f"{group['id']}_{lane_number}",
                    "label": group["label"] if lane_number == 1 else f"{group['label']}{lane_number}",
                    "group": group["id"],
                    "group_label": group["label"],
                    "lifecycle": lifecycle["id"],
                    "lifecycle_label": lifecycle["label"],
                    "lifecycle_sort": lifecycle["sort"],
                    "index": lane_number,
                    "sort": group["sort"] * 100 + lane_number,
                    "event_count": count,
                }
            )

    return tracks


def lifecycle_for_track_group(group_id: str) -> dict[str, Any]:
    lifecycle_id = TRACK_GROUP_LIFECYCLES.get(group_id, "one_time")
    return LIFECYCLE_DEFINITION_BY_ID[lifecycle_id]


def build_buff_name_keys(events: list[dict[str, Any]]) -> set[str]:
    keys = set(EXPLICIT_BUFF_NAME_PREFIXES)
    for event in events:
        category = (event.get("category") or "").lower()
        duration = int(event.get("duration_seconds") or 0)
        if category in {"album", "tournaments"}:
            continue
        if duration and duration < BUFF_MAX_DURATION_SECONDS:
            keys.add(normalize_match_text(event.get("name") or ""))
    return keys


def classify_track_group(event: dict[str, Any], buff_name_keys: set[str] | None = None) -> str:
    category = (event.get("category") or "").lower()
    name = (event.get("name") or "").strip().lower()
    name_key = normalize_match_text(name)
    duration = int(event.get("duration_seconds") or 0)

    if category == "album":
        return "album"
    if name == "tycoon class":
        return "tycoon_class"
    if category == "tournaments":
        return "tournaments"
    if is_buff_name(name_key, buff_name_keys or set()):
        return "buff"
    if duration and duration < BUFF_MAX_DURATION_SECONDS:
        return "buff"
    if category in {"dig minigame", "partner events"}:
        return "minigames"
    if category in {"golden blitz"} or name in ONE_TIME_EVENT_NAMES:
        return "one_time"
    if category == "special events":
        return "minigames"
    return "one_time"


def is_buff_name(name_key: str, buff_name_keys: set[str]) -> bool:
    return name_key in buff_name_keys or any(name_key.startswith(prefix) for prefix in EXPLICIT_BUFF_NAME_PREFIXES)


def first_non_overlapping_lane(lane_ends: list[int], start_timestamp: int) -> int:
    for index, lane_end in enumerate(lane_ends):
        if lane_end <= start_timestamp:
            return index
    return len(lane_ends)


def build_article_record(
    post: PostLink,
    title: str,
    published_date: str | None,
    content: Tag,
    soup: BeautifulSoup,
) -> dict[str, Any]:
    body_text = clean_text(content.get_text(" ", strip=True))
    article_type = classify_article(post.url, title, body_text)
    summary = extract_summary(content) or post.excerpt
    image = soup.select_one("meta[property='og:image']")
    record: dict[str, Any] = {
        "id": build_article_id(title, post.url),
        "type": article_type,
        "url": post.url,
        "title": title,
        "published_date": published_date,
        "summary": summary,
        "sections": extract_sections(content),
        "image_url": image.get("content") if image else None,
    }

    album = extract_album(content, title)
    if not album and article_type == "album":
        album = extract_album_overview(content, title)
    if album:
        record["album"] = album

    return record


def classify_article(url: str, title: str, body_text: str) -> str:
    text = f"{url} {title} {body_text[:500]}".lower()
    if "/todays-events-" in url:
        return "daily_events"
    if "album" in text:
        return "album"
    if "golden blitz" in text or "golden-blitz" in text:
        return "golden_blitz"
    if "partner" in text:
        return "partner_event"
    if "treasure" in text or "dig minigame" in text:
        return "dig_minigame"
    if "free dice" in text or "reward links" in text:
        return "reward_links"
    return "general"


def extract_summary(content: Tag) -> str | None:
    parts: list[str] = []
    for node in content.find_all(["p", "li"], recursive=True):
        text = clean_text(node.get_text(" ", strip=True))
        if not text or should_skip_article_text(text):
            continue
        parts.append(text)
        if len(parts) >= 3:
            break

    if not parts:
        return None

    summary = " ".join(parts)
    return summary[:600].rstrip()


def extract_sections(content: Tag) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    for node in content.find_all(["h1", "h2", "h3", "h4", "p", "li"], recursive=True):
        text = clean_text(node.get_text(" ", strip=True))
        if not text or should_skip_article_text(text):
            continue

        if node.name in {"h1", "h2", "h3", "h4"}:
            heading = clean_heading(text)
            if not heading or heading.lower() == "read more":
                current = None
                continue
            current = {"heading": heading, "items": []}
            sections.append(current)
            if len(sections) >= 12:
                break
            continue

        if current is None:
            continue
        current["items"].append(text)
        current["items"] = current["items"][:30]

    return [section for section in sections if section["items"]]


def extract_album(content: Tag, title: str) -> dict[str, Any] | None:
    sets: list[dict[str, Any]] = []
    current_set: dict[str, Any] | None = None

    seen_stickers_by_set: dict[int, set[str]] = {}

    for node in content.find_all(["h1", "h2", "h3", "p", "li", "div", "span"], recursive=True):
        text = clean_text(node.get_text(" ", strip=True))
        if not text or should_skip_article_text(text):
            continue

        set_match = re.match(r"#?(\d+):\s*(.+)", clean_heading(text))
        if node.name in {"h1", "h2", "h3"} and set_match:
            current_set = {
                "number": int(set_match.group(1)),
                "name": set_match.group(2),
                "stickers": [],
            }
            sets.append(current_set)
            seen_stickers_by_set[current_set["number"]] = set()
            continue

        if current_set is None:
            continue

        sticker = parse_sticker_line(text)
        if sticker and sticker["name"] not in seen_stickers_by_set[current_set["number"]]:
            seen_stickers_by_set[current_set["number"]].add(sticker["name"])
            current_set["stickers"].append(sticker)

    if not sets:
        return None

    stickers = [sticker for album_set in sets for sticker in album_set["stickers"]]
    return {
        "name": extract_album_name(title, content.get_text(" ", strip=True)),
        "set_count": len(sets),
        "sticker_count": len(stickers),
        "gold_sticker_count": sum(1 for sticker in stickers if sticker["type"].lower() == "gold"),
        "sets": sets,
    }


def extract_album_overview(content: Tag, title: str) -> dict[str, Any] | None:
    text = clean_text(content.get_text(" ", strip=True))
    if "album" not in text.lower():
        return None

    set_count_match = re.search(r"(\d+)\s+(?:unique\s+)?sticker sets?", text, flags=re.IGNORECASE)
    run_start_text, run_end_text = extract_album_run_dates(text)
    if not run_start_text:
        run_start_text = extract_album_start_date(text)

    rewards: list[str] = []
    for node in content.find_all(["li", "p"], recursive=True):
        item = clean_text(node.get_text(" ", strip=True))
        if not item or should_skip_article_text(item):
            continue
        if re.search(r"\b(dice|token|cash|reward|shield|emoji)\b", item, flags=re.IGNORECASE):
            rewards.append(item)
        if len(rewards) >= 8:
            break

    album: dict[str, Any] = {
        "name": extract_album_name(title, text),
        "set_count": int(set_count_match.group(1)) if set_count_match else None,
        "sticker_count": None,
        "gold_sticker_count": None,
        "run_start_text": run_start_text,
        "run_end_text": run_end_text,
        "rewards": rewards,
        "related_links": extract_album_links(content),
        "sets": [],
    }
    return album


def extract_album_run_dates(text: str) -> tuple[str | None, str | None]:
    date = ALBUM_DATE_TEXT_PATTERN
    patterns = (
        rf"(?:running|runs)\s+from\s+({date})\s+(?:through|to|-)\s+({date})",
        rf"(?:launch(?:es|ing)?|arrives|kicks off|starts|begins)\s+(?:on\s+)?({date})"
        rf".{{0,320}}?\brun(?:s|ning)?(?:\s+all\s+the\s+way)?\s+(?:through|until|to|-)\s+({date})",
        rf"({date})\s*(?:-|–|through|to|until)\s*({date})",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return clean_text(match.group(1)), clean_text(match.group(2))
    return None, None


def extract_album_start_date(text: str) -> str | None:
    match = re.search(
        rf"(?:launch(?:es|ing)?|arrives|kicks off|starts|begins|starting)\s+(?:on\s+)?({ALBUM_DATE_TEXT_PATTERN})",
        text,
        flags=re.IGNORECASE,
    )
    return clean_text(match.group(1)) if match else None


def extract_album_name(title: str, body_text: str) -> str:
    quoted = re.search(r"[\"“](.+?)[\"”]\s+Album", title)
    if quoted:
        return clean_text(quoted.group(1))

    title_patterns = (
        r"^Get Ready for the Next Album:\s*(.+)$",
        r"^(?:Upcoming|Next) Album:\s*(?:Get Ready for\s+)?(.+?)(?:\s+and\s+\d+-Star\b.*)?$",
        r"^Inside\s+([^:]+):",
        r"Next Album Is[.…: ]+\s*(.+)$",
        r"^.*?([A-Z][A-Za-z0-9 !'&:-]+?)\s+Album\s*(?:[–-]|:|$)",
    )
    for pattern in title_patterns:
        match = re.search(pattern, title, flags=re.IGNORECASE)
        if match:
            return clean_album_name(match.group(1))

    named = re.search(r"([A-Z][A-Za-z0-9 !'&:-]+?)\s+is\s+the\s+next\s+sticker album", body_text)
    if named:
        name = clean_album_name(named.group(1))
        if name.lower() not in {"it", "this", "that"}:
            return name

    album_action = re.search(
        rf"\b([A-Z][A-Za-z0-9 !'&:-]+?)\s+album\s+"
        r"(?:kicks off|launches|arrives|is|runs|wraps|ends|will)",
        body_text,
        flags=re.IGNORECASE,
    )
    if album_action:
        return clean_album_name(album_action.group(1))

    return clean_event_title(title)


def clean_album_name(value: str) -> str:
    name = clean_text(value)
    name = re.sub(r"\s+Album\b.*$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s+[–-]\s+.*$", "", name)
    name = re.sub(r"\s+Your Next Sticker Adventure Begins!?$", "", name, flags=re.IGNORECASE)
    return name.strip(" .!:-")


def extract_album_links(content: Tag) -> list[dict[str, str]]:
    links: list[dict[str, str]] = []
    seen_urls: set[str] = set()
    for link in content.select("a[href]"):
        text = clean_text(link.get_text(" ", strip=True))
        url = urljoin(BASE_URL, link["href"])
        lowered = f"{text} {url}".lower()
        if "album" not in lowered and "sticker" not in lowered:
            continue
        if url in seen_urls:
            continue
        seen_urls.add(url)
        links.append({"title": text or url, "url": url})
    return links[:10]


def parse_sticker_line(text: str) -> dict[str, Any] | None:
    match = re.match(r"(.+?),\s*(\d+)\s*Stars?,\s*(Standard|Gold)$", text, flags=re.IGNORECASE)
    if not match:
        return None

    return {
        "name": match.group(1).strip(),
        "stars": int(match.group(2)),
        "type": match.group(3).title(),
    }


def should_skip_article_text(text: str) -> bool:
    lowered = text.lower()
    skip_fragments = (
        "new insider special",
        "join insider",
        "download the app",
        "read more",
        "by monopoly go! wiki",
        "need to finish your album?",
    )
    return any(fragment in lowered for fragment in skip_fragments)


def clean_heading(text: str) -> str:
    return clean_text(text).lstrip("#").strip()


def clean_event_title(title: str) -> str:
    title = re.sub(r"^today's events\s*\([^)]+\)\s*-?\s*", "", title, flags=re.IGNORECASE)
    title = re.sub(r":\s*coming\s+.+$", "", title, flags=re.IGNORECASE)
    title = re.sub(r"\s+album\s*[–-].*$", " Album", title, flags=re.IGNORECASE)
    return clean_text(title)


def compact_article_reference(article: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": article["type"],
        "title": article["title"],
        "url": article["url"],
        "published_date": article.get("published_date"),
    }


def article_type_to_category(article_type: str) -> str:
    return {
        "golden_blitz": "Golden Blitz",
        "partner_event": "Partner Events",
        "dig_minigame": "Dig Minigame",
    }.get(article_type, "Special Events")


def normalize_match_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def build_article_id(title: str, url: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    if slug:
        return f"{COMPETITOR_NAME}:article:{slug}"
    fallback = re.sub(r"[^a-z0-9]+", "-", urlparse(url).path.strip("/").lower()).strip("-")
    return f"{COMPETITOR_NAME}:article:{fallback}"


def extract_event_name(block: Tag) -> str:
    link = block.select_one("a.event-link-title")
    if link:
        return clean_text(link.get_text(" ", strip=True))

    bold_span = block.select_one('span[style*="font-weight:bold"]')
    if bold_span:
        return clean_text(bold_span.get_text(" ", strip=True))

    first_child = block.find("div", recursive=False)
    if first_child:
        for unwanted in first_child.select(".local-date, img"):
            unwanted.extract()
        return clean_text(first_child.get_text(" ", strip=True))

    return ""


def extract_duration(block: Tag) -> str | None:
    for span in block.find_all("span"):
        text = clean_text(span.get_text(" ", strip=True))
        if text.startswith("Duration:"):
            return text.removeprefix("Duration:").strip()
    return None


def build_event_id(name: str, start_timestamp: int, end_timestamp: int) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return f"{COMPETITOR_NAME}:{slug}:{start_timestamp}:{end_timestamp}"


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()
