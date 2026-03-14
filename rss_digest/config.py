from __future__ import annotations

import os
from dataclasses import dataclass


def _as_int(env_name: str, default: int) -> int:
    value = os.getenv(env_name)
    if not value:
        return default
    return int(value)


def _as_bool(env_name: str, default: bool) -> bool:
    value = os.getenv(env_name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _resolve_bilibili_cookie(uid: str) -> str:
    if uid:
        uid_key = f"BILIBILI_COOKIE_{uid}"
        uid_cookie = os.getenv(uid_key, "").strip()
        if uid_cookie:
            return uid_cookie
    return os.getenv("BILIBILI_COOKIE", "").strip()


@dataclass(frozen=True)
class AppConfig:
    openrouter_api_key: str
    openrouter_base_url: str
    model_text_default: str
    model_video_default: str
    digest_window_days: int
    request_timeout_seconds: int
    max_items_per_feed: int
    feed_user_agent: str
    bilibili_uid: str
    bilibili_cookie: str
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_app_password: str
    digest_email_to: str
    digest_email_from: str
    dry_run: bool

    @staticmethod
    def from_env(dry_run_override: bool | None = None) -> "AppConfig":
        dry_run = _as_bool("DRY_RUN", False) if dry_run_override is None else dry_run_override
        smtp_user = os.getenv("GMAIL_SMTP_USER", "").strip()

        return AppConfig(
            openrouter_api_key=os.getenv("OPENROUTER_API_KEY", "").strip(),
            openrouter_base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").strip(),
            model_text_default=os.getenv("MODEL_TEXT_DEFAULT", "openai/gpt-4o-mini").strip(),
            model_video_default=os.getenv("MODEL_VIDEO_DEFAULT", "google/gemini-1.5-flash").strip(),
            digest_window_days=_as_int("DIGEST_WINDOW_DAYS", 7),
            request_timeout_seconds=_as_int("REQUEST_TIMEOUT_SECONDS", 45),
            max_items_per_feed=_as_int("MAX_ITEMS_PER_FEED", 20),
            feed_user_agent=os.getenv(
                "FEED_USER_AGENT",
                (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                ),
            ).strip(),
            bilibili_uid=os.getenv("BILIBILI_UID", "").strip(),
            bilibili_cookie=_resolve_bilibili_cookie(os.getenv("BILIBILI_UID", "").strip()),
            smtp_host=os.getenv("GMAIL_SMTP_HOST", "smtp.gmail.com").strip(),
            smtp_port=_as_int("GMAIL_SMTP_PORT", 587),
            smtp_user=smtp_user,
            smtp_app_password=os.getenv("GMAIL_SMTP_APP_PASSWORD", "").strip(),
            digest_email_to=os.getenv("DIGEST_EMAIL_TO", "").strip(),
            digest_email_from=os.getenv("DIGEST_EMAIL_FROM", smtp_user).strip(),
            dry_run=dry_run,
        )

    def validate(self, require_openrouter: bool = True, require_email: bool = True) -> None:
        missing = []
        if require_openrouter and not self.openrouter_api_key:
            missing.append("OPENROUTER_API_KEY")

        if require_email and not self.dry_run:
            if not self.smtp_user:
                missing.append("GMAIL_SMTP_USER")
            if not self.smtp_app_password:
                missing.append("GMAIL_SMTP_APP_PASSWORD")
            if not self.digest_email_to:
                missing.append("DIGEST_EMAIL_TO")

        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
