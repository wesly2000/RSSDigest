from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from urllib.parse import parse_qs, urlparse

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    CouldNotRetrieveTranscript,
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
)


class SubtitleExtractor(ABC):
    @abstractmethod
    def can_handle(self, url: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def extract_subtitle(self, url: str) -> str | None:
        raise NotImplementedError


class YouTubeSubtitleExtractor(SubtitleExtractor):
    def __init__(self) -> None:
        self._client = YouTubeTranscriptApi()

    def can_handle(self, url: str) -> bool:
        host = urlparse(url or "").netloc.lower()
        return "youtube.com" in host or "youtu.be" in host

    def extract_subtitle(self, url: str) -> str | None:
        video_id = _extract_youtube_video_id(url)
        if not video_id:
            return None

        try:
            transcript_items = self._client.fetch(video_id)
        except (
            NoTranscriptFound,
            TranscriptsDisabled,
            VideoUnavailable,
            CouldNotRetrieveTranscript,
        ):
            return None
        except Exception as exc:  # noqa: BLE001
            logging.warning("Unexpected YouTube subtitle extraction error for %s: %s", url, exc)
            return None

        text_parts: list[str] = []
        for item in transcript_items:
            text = ""
            if isinstance(item, dict):
                text = str(item.get("text", "")).strip()
            else:
                text = str(getattr(item, "text", "")).strip()
            if text:
                text_parts.append(text)
        subtitle_text = " ".join(part for part in text_parts if part).strip()
        return subtitle_text or None


class BilibiliSubtitleExtractor(SubtitleExtractor):
    def can_handle(self, url: str) -> bool:
        host = urlparse(url or "").netloc.lower()
        return "bilibili.com" in host or "b23.tv" in host

    def extract_subtitle(self, url: str) -> str | None:
        raise NotImplementedError("Bilibili subtitle extraction is not implemented yet.")


class NetflixSubtitleExtractor(SubtitleExtractor):
    def can_handle(self, url: str) -> bool:
        host = urlparse(url or "").netloc.lower()
        return "netflix.com" in host

    def extract_subtitle(self, url: str) -> str | None:
        raise NotImplementedError("Netflix subtitle extraction is not implemented yet.")


class SubtitleExtractorRegistry:
    def __init__(self) -> None:
        self._extractors: list[SubtitleExtractor] = [
            YouTubeSubtitleExtractor(),
            BilibiliSubtitleExtractor(),
            NetflixSubtitleExtractor(),
        ]

    def extract_subtitle(self, url: str) -> str | None:
        for extractor in self._extractors:
            if not extractor.can_handle(url):
                continue
            try:
                return extractor.extract_subtitle(url)
            except NotImplementedError:
                logging.info("Subtitle extractor not implemented for URL: %s", url)
                return None
        return None


def _extract_youtube_video_id(url: str) -> str:
    parsed = urlparse(url or "")
    host = parsed.netloc.lower()
    path = parsed.path.strip("/")

    if "youtu.be" in host:
        return path.split("/", 1)[0] if path else ""

    if "youtube.com" not in host:
        return ""

    if path == "watch":
        return parse_qs(parsed.query).get("v", [""])[0]

    path_parts = [part for part in path.split("/") if part]
    if len(path_parts) >= 2 and path_parts[0] in {"shorts", "embed", "live", "v"}:
        return path_parts[1]

    return ""
