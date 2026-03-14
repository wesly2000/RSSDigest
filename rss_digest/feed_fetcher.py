from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from time import struct_time
from typing import Iterable
from urllib.parse import urlparse

import feedparser

from rss_digest.types import FeedEntry, FeedSubscription


@dataclass(frozen=True)
class FeedCheckResult:
    xml_url: str
    status: int | None
    total_entries: int
    entries_in_window: int


def _parse_entry_datetime(entry: feedparser.FeedParserDict) -> datetime | None:
    for key in ("published_parsed", "updated_parsed", "created_parsed"):
        value = entry.get(key)
        if isinstance(value, struct_time):
            return datetime(*value[:6], tzinfo=timezone.utc)

    for key in ("published", "updated", "created"):
        value = entry.get(key)
        if value:
            try:
                parsed = parsedate_to_datetime(value)
                if parsed.tzinfo is None:
                    return parsed.replace(tzinfo=timezone.utc)
                return parsed.astimezone(timezone.utc)
            except (TypeError, ValueError):
                continue
    return None


def _extract_content(entry: feedparser.FeedParserDict) -> str:
    contents = entry.get("content")
    if contents and isinstance(contents, list):
        value = contents[0].get("value")
        if value:
            return str(value)
    summary = entry.get("summary")
    if summary:
        return str(summary)
    description = entry.get("description")
    if description:
        return str(description)
    return ""


def _is_bilibili_feed_url(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path.lower()
    return "bilibili" in host or "/bilibili/" in path


def fetch_recent_entries(
    subscriptions: Iterable[FeedSubscription],
    since_utc: datetime,
    until_utc: datetime,
    max_items_per_feed: int,
    user_agent: str,
    bilibili_cookie: str = "",
) -> list[FeedEntry]:
    output: list[FeedEntry] = []
    for subscription in subscriptions:
        headers = {"User-Agent": user_agent}
        if bilibili_cookie and _is_bilibili_feed_url(subscription.xml_url):
            headers["Cookie"] = bilibili_cookie
        try:
            parsed = feedparser.parse(
                subscription.xml_url,
                request_headers=headers,
            )
        except Exception as exc:  # noqa: BLE001
            logging.warning("Failed to fetch feed %s: %s", subscription.xml_url, exc)
            continue

        for entry in parsed.entries[:max_items_per_feed]:
            published_at = _parse_entry_datetime(entry)
            if not published_at:
                continue
            if published_at < since_utc or published_at > until_utc:
                continue
            title = str(entry.get("title", "Untitled")).strip() or "Untitled"
            url = str(entry.get("link", "")).strip() or subscription.html_url or subscription.xml_url
            output.append(
                FeedEntry(
                    subscription=subscription,
                    title=title,
                    url=url,
                    published_at=published_at,
                    content=_extract_content(entry),
                )
            )
    output.sort(key=lambda item: item.published_at, reverse=True)
    return output


def check_feed_availability(
    subscriptions: Iterable[FeedSubscription],
    since_utc: datetime,
    until_utc: datetime,
    user_agent: str,
    bilibili_cookie: str = "",
) -> list[FeedCheckResult]:
    checks: list[FeedCheckResult] = []
    for subscription in subscriptions:
        headers = {"User-Agent": user_agent}
        if bilibili_cookie and _is_bilibili_feed_url(subscription.xml_url):
            headers["Cookie"] = bilibili_cookie

        try:
            parsed = feedparser.parse(
                subscription.xml_url,
                request_headers=headers,
            )
        except Exception:  # noqa: BLE001
            checks.append(
                FeedCheckResult(
                    xml_url=subscription.xml_url,
                    status=None,
                    total_entries=0,
                    entries_in_window=0,
                )
            )
            continue

        in_window = 0
        for entry in parsed.entries:
            published_at = _parse_entry_datetime(entry)
            if not published_at:
                continue
            if since_utc <= published_at <= until_utc:
                in_window += 1

        checks.append(
            FeedCheckResult(
                xml_url=subscription.xml_url,
                status=parsed.get("status"),
                total_entries=len(parsed.entries),
                entries_in_window=in_window,
            )
        )
    return checks
