from __future__ import annotations

import logging
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from time import struct_time
from typing import Iterable

import feedparser

from rss_digest.types import FeedEntry, FeedSubscription


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


def fetch_recent_entries(
    subscriptions: Iterable[FeedSubscription],
    since_utc: datetime,
    until_utc: datetime,
    max_items_per_feed: int,
    user_agent: str,
) -> list[FeedEntry]:
    output: list[FeedEntry] = []
    for subscription in subscriptions:
        try:
            parsed = feedparser.parse(
                subscription.xml_url,
                request_headers={"User-Agent": user_agent},
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
