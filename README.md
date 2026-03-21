# RSS Digest With Weekly Email

This project reads RSS sources from an OPML file, fetches updates for the last 7 days by default, summarizes each update with OpenRouter models, and sends a Markdown report to Gmail.

## Features

- Parse OPML hierarchy as `category -> topic -> feed`.
- Attach feed metadata to each digest entry:
  - `author`
  - `category`
  - `topic`
  - `url`
- Route model by category:
  - `Videos` (and audio-like categories) -> try subtitle extraction first.
  - subtitle found -> summarize subtitle with default text model.
  - subtitle unavailable -> fallback to video/multimodal model.
  - all other categories -> default text model.
- Output digest report in Markdown with this per-item format:
  - `[title][digest][author][date][category][topic][url]` (date format: `YYYY-MM-DD`)
- Digest language follows the dominant language of each source item (for example, Chinese source -> Chinese digest, English source -> English digest).
- Send report via Gmail SMTP (App Password).
- Run automatically in GitHub Actions every Saturday at 08:00 UTC.

## Project Structure

- `main.py` - CLI entrypoint.
- `rss_digest/opml_parser.py` - OPML parser.
- `rss_digest/xml_parsers.py` - XML parser strategy classes (default/YouTube/Bilibili).
- `rss_digest/subtitle_extractors.py` - subtitle extractor strategy classes (YouTube/Bilibili/Netflix).
- `rss_digest/feed_fetcher.py` - fetch + time filtering.
- `rss_digest/model_router.py` - category-based model selection.
- `rss_digest/openrouter_client.py` - OpenRouter chat completions client.
- `rss_digest/report_renderer.py` - Markdown renderer.
- `rss_digest/email_sender.py` - Gmail SMTP sender.

## Local Setup

1. Install Python 3.11+.
2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and fill values.

Required values:

- `OPENROUTER_API_KEY`
- `GMAIL_SMTP_USER`
- `GMAIL_SMTP_APP_PASSWORD`
- `DIGEST_EMAIL_TO`

Useful defaults:

- `DIGEST_WINDOW_DAYS=7`
- `MODEL_TEXT_DEFAULT=deepseek/deepseek-chat`
- `MODEL_VIDEO_DEFAULT=google/gemini-2.5-flash-lite`
- `FEED_USER_AGENT=<Chrome UA string>`
- `BILIBILI_UID=<optional uid used for uid-scoped cookie lookup>`
- `BILIBILI_COOKIE=<optional fallback cookie string for RSSHub BiliBili routes>`
- `BILIBILI_COOKIE_{uid}=<preferred uid-scoped cookie, e.g. BILIBILI_COOKIE_438767999>`

Dependency note:

- `youtube-transcript-api` is used for YouTube subtitle extraction.

## Run Locally

Dry run (generate markdown only, no email):

```powershell
python main.py --opml follow.opml --dry-run --output reports/latest_digest.md
```

Full run (generate + send email):

```powershell
python main.py --opml follow.opml --output reports/latest_digest.md
```

Optional override window:

```powershell
python main.py --opml follow.opml --window-days 7 --output reports/latest_digest.md
```

Feed availability check only (no model calls, no email):

```powershell
python main.py --opml follow.opml --check-feeds-only
```

## GitHub Actions Automation

Workflow file: `.github/workflows/weekly-digest.yml`

Triggers:

- Weekly on Saturday at 08:00 UTC.
- Manual run via `workflow_dispatch`.

Set these repository secrets:

- `OPENROUTER_API_KEY`
- `OPENROUTER_BASE_URL` (optional; defaults to OpenRouter API v1 URL)
- `MODEL_TEXT_DEFAULT` (optional)
- `MODEL_VIDEO_DEFAULT` (optional)
- `DIGEST_WINDOW_DAYS` (optional)
- `BILIBILI_UID` (optional, when using uid-scoped cookie keys)
- `BILIBILI_COOKIE` (optional, recommended if BiliBili routes are blocked)
- `GMAIL_SMTP_HOST` (optional, usually `smtp.gmail.com`)
- `GMAIL_SMTP_PORT` (optional, usually `587`)
- `GMAIL_SMTP_USER`
- `GMAIL_SMTP_APP_PASSWORD`
- `DIGEST_EMAIL_TO`
- `DIGEST_EMAIL_FROM` (optional)

## Gmail App Password Notes

- Enable 2-Step Verification on your Google account.
- Generate an App Password for Mail.
- Use that value as `GMAIL_SMTP_APP_PASSWORD`.

## Troubleshooting

- Missing env vars:
  - The app raises a clear error listing required variables.
- Some feeds fail:
  - The app logs warning and continues processing other feeds.
  - For BiliBili/RSSHub routes, set `BILIBILI_UID` + `BILIBILI_COOKIE_{uid}` (preferred) or fallback `BILIBILI_COOKIE`.
- Subtitles unavailable for video items:
  - The app falls back to `MODEL_VIDEO_DEFAULT` for that item.
  - Subtitle extraction failures are non-fatal and only impact per-item routing.
- No updates found:
  - Report still generated with a `No updates` section.

## BiliBili Cookie Notes

- `BILIBILI_COOKIE_{uid}` is used first when `BILIBILI_UID` is set.
- If uid-scoped key is absent, fallback `BILIBILI_COOKIE` is used.
- Cookie is only attached to BiliBili-related feed requests.
- Keep this value secret; never commit it into the repository.
- Use local `.env` for development and GitHub Actions encrypted secrets for automation.

## XML Parser Modularization

- `parse_opml` handles OPML traversal and metadata extraction only.
- Site-specific URL handling is delegated to parser strategies in `rss_digest/xml_parsers.py`.
- Current strategies:
  - `YouTubeXMLParser`: resolves `@handle` and channel URLs to official YouTube RSS.
  - `BilibiliXMLParser`: currently no-op/default behavior (placeholder for future logic).
  - `DefaultXMLParser`: keeps original `xmlUrl`.
