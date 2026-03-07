from __future__ import annotations

from rss_digest.config import AppConfig
from rss_digest.types import FeedEntry


def select_model_for_entry(entry: FeedEntry, config: AppConfig) -> tuple[str, str]:
    category = entry.subscription.category.strip().lower()
    if category in {"videos", "video"}:
        return config.model_video_default, "video category detected"
    if category in {"audios", "audio", "podcast", "podcasts"}:
        return config.model_video_default, "audio category uses multimodal model"
    return config.model_text_default, "text/image category uses default text model"
