from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Iterable

from rss_digest.types import DigestItem


def render_markdown(
    digests: Iterable[DigestItem],
    generated_at_utc: datetime,
    since_utc: datetime,
    until_utc: datetime,
) -> str:
    grouped: dict[str, dict[str, list[DigestItem]]] = defaultdict(lambda: defaultdict(list))
    for item in digests:
        grouped[item.category][item.topic].append(item)

    lines = [
        "# RSS Digest Report",
        "",
        f"- Generated (UTC): `{generated_at_utc.isoformat()}`",
        f"- Window (UTC): `{since_utc.isoformat()}` to `{until_utc.isoformat()}`",
        "",
        "Each entry follows: `[title][digest][author][category][topic][url]`",
        "",
    ]

    if not grouped:
        lines.extend(
            [
                "## No updates",
                "",
                "No feed entries were found in the configured time period.",
                "",
            ]
        )
        return "\n".join(lines)

    for category in sorted(grouped.keys()):
        lines.append(f"## Category: {category}")
        lines.append("")
        for topic in sorted(grouped[category].keys()):
            lines.append(f"### Topic: {topic}")
            lines.append("")
            for digest in grouped[category][topic]:
                sanitized = digest.digest.replace("\n", " ").strip()
                lines.append(
                    f"- [{digest.title}]"
                    f"[{sanitized}]"
                    f"[{digest.author}]"
                    f"[{digest.category}]"
                    f"[{digest.topic}]"
                    f"[{digest.url}]"
                )
            lines.append("")
    return "\n".join(lines)
