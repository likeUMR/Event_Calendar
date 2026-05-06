from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from 获取数据.monopolygo_wiki.collector import (
    BASE_URL,
    COMPETITOR_NAME,
    LISTING_URL,
    SOURCE_NAME,
    SUPPLEMENTAL_SOURCE_PAGES,
    SUPPLEMENTAL_SOURCE_URLS,
    PostLink,
    build_listing_url,
    clean_text,
    dedupe_posts,
    is_collectable_post_url,
)


class MonopolyGoWikiRawCollector:
    """Download and cache raw Monopoly GO wiki pages."""

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

    def collect_raw(
        self,
        pages: int = 1,
        max_posts: int | None = None,
        source_url: str = LISTING_URL,
        supplemental_source_urls: tuple[str, ...] = SUPPLEMENTAL_SOURCE_URLS,
        supplemental_source_pages: int = SUPPLEMENTAL_SOURCE_PAGES,
    ) -> dict[str, Any]:
        listing_pages = self.fetch_listing_pages(pages=pages, source_url=source_url)
        supplemental_pages: list[dict[str, Any]] = []
        posts: list[PostLink] = []

        for page in listing_pages:
            posts.extend(discover_posts_from_html(page["html"]))

        for supplemental_url in supplemental_source_urls:
            pages_for_source = self.fetch_listing_pages(pages=supplemental_source_pages, source_url=supplemental_url)
            supplemental_pages.extend(pages_for_source)
            for page in pages_for_source:
                posts.extend(discover_posts_from_html(page["html"]))

        posts = dedupe_posts(posts)
        if max_posts is not None:
            posts = posts[:max_posts]

        raw_posts: list[dict[str, Any]] = []
        for index, post in enumerate(posts):
            if index:
                time.sleep(self.request_delay)
            raw_posts.append(
                {
                    "url": post.url,
                    "title": post.title,
                    "published_date": post.published_date,
                    "excerpt": post.excerpt,
                    "html": self.fetch(post.url),
                }
            )

        return {
            "schema_version": "1.0",
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "competitor": COMPETITOR_NAME,
            "source": SOURCE_NAME,
            "listing_source_url": source_url,
            "supplemental_source_urls": list(supplemental_source_urls),
            "request": {
                "pages": pages,
                "max_posts": max_posts,
                "supplemental_source_pages": supplemental_source_pages,
            },
            "listing_pages": listing_pages,
            "supplemental_pages": supplemental_pages,
            "posts": raw_posts,
        }

    def fetch_listing_pages(self, pages: int, source_url: str) -> list[dict[str, Any]]:
        return [self.fetch_listing_page(build_listing_url(source_url, page_index)) for page_index in range(pages)]

    def fetch_listing_page(self, url: str) -> dict[str, Any]:
        return {
            "url": url,
            "html": self.fetch(url),
        }

    def fetch(self, url: str) -> str:
        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()
        return response.text


def discover_posts_from_html(html: str) -> list[PostLink]:
    posts: list[PostLink] = []
    seen_urls: set[str] = set()
    soup = BeautifulSoup(html, "html.parser")

    for article in soup.select("article.gh-card, article"):
        link = article.select_one("a.gh-card-link[href]") or article.select_one("a[href]")
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
        return posts

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
