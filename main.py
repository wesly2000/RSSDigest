from __future__ import annotations

import argparse
import logging
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

from rss_digest.config import AppConfig
from rss_digest.email_sender import send_digest_email
from rss_digest.feed_fetcher import fetch_recent_entries
from rss_digest.model_router import select_model_for_entry
from rss_digest.openrouter_client import OpenRouterClient
from rss_digest.opml_parser import parse_opml
from rss_digest.report_renderer import render_markdown
from rss_digest.types import DigestItem


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate weekly RSS digest report.")
    parser.add_argument("--opml", default="follow.opml", help="Path to OPML subscriptions file.")
    parser.add_argument("--window-days", type=int, default=None, help="Digest lookback in days.")
    parser.add_argument("--dry-run", action="store_true", help="Skip email and write markdown only.")
    parser.add_argument(
        "--output",
        default="reports/latest_digest.md",
        help="Where to write generated markdown report.",
    )
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    load_dotenv()
    args = parse_args()

    config = AppConfig.from_env(dry_run_override=args.dry_run)
    if args.window_days and args.window_days > 0:
        config = replace(config, digest_window_days=args.window_days)
    config.validate()

    opml_path = Path(args.opml).resolve()
    subscriptions = parse_opml(opml_path)
    logging.info("Parsed %s feed subscriptions from %s", len(subscriptions), opml_path)

    now_utc = datetime.now(timezone.utc)
    since_utc = now_utc - timedelta(days=config.digest_window_days)
    entries = fetch_recent_entries(
        subscriptions=subscriptions,
        since_utc=since_utc,
        until_utc=now_utc,
        max_items_per_feed=config.max_items_per_feed,
        user_agent=config.feed_user_agent,
        bilibili_cookie=config.bilibili_cookie,
    )
    logging.info("Fetched %s feed entries in range", len(entries))

    client = OpenRouterClient(config)
    digests: list[DigestItem] = []
    for entry in entries:
        model, reason = select_model_for_entry(entry, config)
        logging.info("Summarizing '%s' with model '%s' (%s)", entry.title, model, reason)
        digest_text = client.summarize(entry, model=model)
        digests.append(
            DigestItem(
                title=entry.title,
                digest=digest_text,
                author=entry.subscription.author,
                category=entry.subscription.category,
                topic=entry.subscription.topic,
                url=entry.url,
                model=model,
                published_at=entry.published_at,
            )
        )

    markdown = render_markdown(
        digests=digests,
        generated_at_utc=now_utc,
        since_utc=since_utc,
        until_utc=now_utc,
    )
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")
    logging.info("Digest markdown written to %s", output_path)

    if config.dry_run:
        logging.info("Dry run enabled. Email sending skipped.")
        return

    send_digest_email(
        config=config,
        subject=f"Weekly RSS Digest ({since_utc.date()} to {now_utc.date()})",
        markdown_body=markdown,
    )
    logging.info("Digest email sent to %s", config.digest_email_to)


if __name__ == "__main__":
    main()
