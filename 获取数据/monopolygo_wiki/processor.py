from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from 获取数据.monopolygo_wiki.collector import (
    COMPETITOR_NAME,
    LIFECYCLE_DEFINITIONS,
    SOURCE_NAME,
    PostLink,
    MonopolyGoWikiCollector,
    assign_event_tracks,
    build_album_events,
    merge_named_minigames,
)
from 获取数据.monopolygo_wiki.raw import discover_posts_from_html


class MonopolyGoWikiRawProcessor:
    """Transform cached raw Monopoly GO wiki HTML into processed calendar data."""

    def __init__(self) -> None:
        self.parser = MonopolyGoWikiCollector()

    def process(self, raw_payload: dict[str, Any]) -> dict[str, Any]:
        events: list[dict[str, Any]] = []
        articles: list[dict[str, Any]] = []
        seen_keys: set[tuple[str, str, int, int]] = set()
        seen_article_urls: set[str] = set()
        primary_post_urls = {
            post.url
            for page in raw_payload.get("listing_pages", [])
            for post in discover_posts_from_html(page.get("html") or "")
        }

        for raw_post in raw_payload.get("posts", []):
            post = PostLink(
                url=raw_post["url"],
                title=raw_post.get("title") or "",
                published_date=raw_post.get("published_date"),
                excerpt=raw_post.get("excerpt"),
            )
            result = self.parser.parse_post_html(post=post, html=raw_post.get("html") or "")
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

        for event in build_album_events(articles, allowed_article_urls=primary_post_urls or None):
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
        self.parser.enrich_events_with_related_articles(events, articles)
        tracks = assign_event_tracks(events)
        events.sort(key=lambda item: (item["start_timestamp"], item["name"]))

        return {
            "schema_version": "1.0",
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "competitor": raw_payload.get("competitor") or COMPETITOR_NAME,
            "source": raw_payload.get("source") or SOURCE_NAME,
            "listing_source_url": raw_payload.get("listing_source_url"),
            "supplemental_source_urls": raw_payload.get("supplemental_source_urls", []),
            "raw_generated_at": raw_payload.get("generated_at"),
            "lifecycles": list(LIFECYCLE_DEFINITIONS),
            "tracks": tracks,
            "articles": articles,
            "events": events,
        }
