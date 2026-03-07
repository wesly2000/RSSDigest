from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from urllib.parse import unquote, urlparse

import requests

_YOUTUBE_CHANNEL_ID_RE = re.compile(r"UC[a-zA-Z0-9_-]{20,}")
_YOUTUBE_HANDLE_CHANNEL_RE = re.compile(r'"channelId":"(UC[a-zA-Z0-9_-]{20,})"')
_DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)


@dataclass(frozen=True)
class FeedResolveContext:
    xml_url: str
    html_url: str
    category: str
    topic: str
    author: str


class XMLParser(ABC):
    @abstractmethod
    def can_handle(self, context: FeedResolveContext) -> bool:
        raise NotImplementedError

    @abstractmethod
    def resolve_xml_url(self, context: FeedResolveContext) -> str:
        raise NotImplementedError


class DefaultXMLParser(XMLParser):
    def can_handle(self, context: FeedResolveContext) -> bool:
        return True

    def resolve_xml_url(self, context: FeedResolveContext) -> str:
        return context.xml_url


class YouTubeXMLParser(XMLParser):
    def __init__(self) -> None:
        self._channel_cache: dict[str, str] = {}

    def can_handle(self, context: FeedResolveContext) -> bool:
        xml_lower = context.xml_url.lower()
        html_lower = context.html_url.lower()
        return (
            "youtube.com" in xml_lower
            or "youtube.com" in html_lower
            or "rsshub.app/youtube/" in xml_lower
            or "rsshub.rssforever.com/youtube/" in xml_lower
        )

    def resolve_xml_url(self, context: FeedResolveContext) -> str:
        xml_url = context.xml_url
        html_url = context.html_url

        if "youtube.com/feeds/videos.xml" in xml_url and "channel_id=" in xml_url:
            return xml_url

        channel_id = self._channel_id_from_url(html_url) or self._channel_id_from_url(xml_url)
        if channel_id:
            return f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"

        handle = self._extract_handle(html_url, xml_url)
        if handle:
            resolved_channel_id = self._resolve_channel_id_from_handle(handle)
            if resolved_channel_id:
                return f"https://www.youtube.com/feeds/videos.xml?channel_id={resolved_channel_id}"

        return xml_url

    @staticmethod
    def _channel_id_from_url(url: str) -> str:
        match = _YOUTUBE_CHANNEL_ID_RE.search(url or "")
        return match.group(0) if match else ""

    @staticmethod
    def _extract_handle(html_url: str, xml_url: str) -> str:
        parsed = urlparse(html_url or "")
        path = unquote(parsed.path or "")
        if "/@" in path:
            return path[path.index("/@") + 1 :].strip("/")

        lowered = (xml_url or "").lower()
        if "/youtube/user/" in lowered:
            tail = (xml_url or "").split("/youtube/user/", 1)[-1].strip("/")
            decoded = unquote(tail)
            if decoded.startswith("@"):
                return decoded
        return ""

    def _resolve_channel_id_from_handle(self, handle: str) -> str:
        if not handle:
            return ""
        if handle in self._channel_cache:
            return self._channel_cache[handle]

        url = f"https://www.youtube.com/{handle}"
        try:
            response = requests.get(
                url,
                headers={"User-Agent": _DEFAULT_USER_AGENT},
                timeout=20,
            )
            response.raise_for_status()
        except Exception as exc:  # noqa: BLE001
            logging.warning("YouTube handle resolve failed for %s: %s", handle, exc)
            self._channel_cache[handle] = ""
            return ""

        match = _YOUTUBE_HANDLE_CHANNEL_RE.search(response.text)
        if match:
            channel_id = match.group(1)
            self._channel_cache[handle] = channel_id
            return channel_id

        fallback = self._channel_id_from_url(response.text)
        if fallback:
            self._channel_cache[handle] = fallback
            return fallback

        logging.warning("YouTube channel_id not found for handle %s", handle)
        self._channel_cache[handle] = ""
        return ""


class BilibiliXMLParser(DefaultXMLParser):
    """Placeholder parser for Bilibili.

    Intentionally uses default/no-op behavior for now; this class exists
    so Bilibili-specific logic can be added later without changing parse_opml.
    """

    def can_handle(self, context: FeedResolveContext) -> bool:
        xml_lower = context.xml_url.lower()
        html_lower = context.html_url.lower()
        return "bilibili" in xml_lower or "bilibili" in html_lower


class XMLParserRegistry:
    def __init__(self) -> None:
        self._parsers: list[XMLParser] = [
            YouTubeXMLParser(),
            BilibiliXMLParser(),
            DefaultXMLParser(),
        ]

    def resolve(self, context: FeedResolveContext) -> str:
        for parser in self._parsers:
            if parser.can_handle(context):
                return parser.resolve_xml_url(context)
        return context.xml_url
