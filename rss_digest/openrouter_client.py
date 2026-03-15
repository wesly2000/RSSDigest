from __future__ import annotations

import json
import logging

import requests

from rss_digest.config import AppConfig
from rss_digest.types import FeedEntry


class OpenRouterClient:
    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._endpoint = f"{config.openrouter_base_url.rstrip('/')}/chat/completions"

    def summarize(self, entry: FeedEntry, model: str, subtitle_text: str | None = None) -> str:
        prompt = self._build_prompt(entry, subtitle_text=subtitle_text)
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You summarize RSS entries for a weekly digest.\n"
                        "First infer the dominant language of the source content "
                        "(from title and content excerpt).\n"
                        "Then write the digest in that same language.\n"
                        "Return only one concise digest paragraph under 120 words."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }
        headers = {
            "Authorization": f"Bearer {self._config.openrouter_api_key}",
            "Content-Type": "application/json",
        }
        try:
            response = requests.post(
                self._endpoint,
                headers=headers,
                data=json.dumps(payload),
                timeout=self._config.request_timeout_seconds,
            )
            response.raise_for_status()
            body = response.json()
            return (
                body.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
                .strip()
            ) or "No digest generated."
        except Exception as exc:  # noqa: BLE001
            logging.warning("OpenRouter summary failed for '%s': %s", entry.title, exc)
            return "Digest unavailable due to model/API error."

    @staticmethod
    def _build_prompt(entry: FeedEntry, subtitle_text: str | None = None) -> str:
        content_preview = entry.content[:4000]
        subtitle_preview = (subtitle_text or "").strip()[:12000]
        body_label = "Video subtitle transcript" if subtitle_preview else "Content excerpt"
        body_content = subtitle_preview if subtitle_preview else content_preview
        return (
            f"Title: {entry.title}\n"
            f"URL: {entry.url}\n"
            f"Author: {entry.subscription.author}\n"
            f"Category: {entry.subscription.category}\n"
            f"Topic: {entry.subscription.topic}\n"
            f"Published UTC: {entry.published_at.isoformat()}\n\n"
            f"{body_label}:\n"
            f"{body_content}"
        )
