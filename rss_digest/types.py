from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class FeedSubscription:
    category: str
    topic: str
    author: str
    xml_url: str
    html_url: str


@dataclass(frozen=True)
class FeedEntry:
    subscription: FeedSubscription
    title: str
    url: str
    published_at: datetime
    content: str


@dataclass(frozen=True)
class DigestItem:
    title: str
    digest: str
    author: str
    category: str
    topic: str
    url: str
    model: str
    published_at: datetime
