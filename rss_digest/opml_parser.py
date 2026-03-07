from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List

from rss_digest.types import FeedSubscription


def _extract_author(raw_text: str) -> str:
    if "|" in raw_text:
        parts = [part.strip() for part in raw_text.split("|") if part.strip()]
        if parts:
            return parts[-1]
    if " - " in raw_text:
        parts = [part.strip() for part in raw_text.split(" - ") if part.strip()]
        if parts:
            return parts[-1]
    return raw_text.strip()


def parse_opml(opml_path: Path) -> List[FeedSubscription]:
    tree = ET.parse(opml_path)
    root = tree.getroot()
    body = root.find("body")
    if body is None:
        return []

    subscriptions: list[FeedSubscription] = []
    for category_node in body.findall("outline"):
        category = (category_node.attrib.get("text") or "Uncategorized").strip()
        for topic_node in category_node.findall("outline"):
            topic = (topic_node.attrib.get("text") or "General").strip()
            for feed_node in topic_node.findall("outline"):
                xml_url = (feed_node.attrib.get("xmlUrl") or "").strip()
                if not xml_url.lower().startswith(("http://", "https://")):
                    continue
                raw_name = (
                    feed_node.attrib.get("title")
                    or feed_node.attrib.get("text")
                    or "Unknown Author"
                ).strip()
                author = _extract_author(raw_name) or "Unknown Author"
                html_url = (feed_node.attrib.get("htmlUrl") or "").strip()
                subscriptions.append(
                    FeedSubscription(
                        category=category or "Uncategorized",
                        topic=topic or "General",
                        author=author,
                        xml_url=xml_url,
                        html_url=html_url,
                    )
                )
    return subscriptions
