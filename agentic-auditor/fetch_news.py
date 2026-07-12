"""Fetches recent AI + Travel & Expense (T&E) audit news from Google News RSS.

Pipeline:
  1. Query Google News RSS for a set of AI/T&E-audit related search terms.
  2. Parse each entry (title, link, published date, summary) with feedparser.
  3. Strip HTML from summaries, robustly parse dates to UTC, and keep only
     entries published in the last 48 hours.
  4. Deduplicate by title, keyword-filter for AI + T&E relevance, sort by
     recency, and write the top 15 to raw_news.json.
"""

import json
import re
from datetime import datetime, timedelta, timezone

import feedparser
from bs4 import BeautifulSoup
from dateutil import parser as dateparser

GOOGLE_NEWS_RSS_TEMPLATE = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"

QUERIES = [
    "AI+agents+expense+audit",
    "agentic+AI+corporate+travel",
    "AI+prepayment+compliance",
    "machine+learning+travel+expense",
]

AI_KEYWORDS = ["ai", "agent", "llm", "automation", "bot", "machine learning", "genai"]
TE_KEYWORDS = ["expense", "travel", "audit", "prepayment", "compliance", "fraud"]

MAX_AGE_HOURS = 48
MAX_RESULTS = 15
OUTPUT_FILE = "raw_news.json"


def strip_html(raw_html):
    if not raw_html:
        return ""
    text = BeautifulSoup(raw_html, "html.parser").get_text(separator=" ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_to_utc(date_str):
    try:
        dt = dateparser.parse(date_str)
    except (ValueError, TypeError, OverflowError):
        return None
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def is_relevant(title, summary):
    haystack = f"{title} {summary}".lower()
    has_ai = any(kw in haystack for kw in AI_KEYWORDS)
    has_te = any(kw in haystack for kw in TE_KEYWORDS)
    return has_ai and has_te


def fetch_entries():
    now_utc = datetime.now(timezone.utc)
    cutoff = now_utc - timedelta(hours=MAX_AGE_HOURS)

    seen_titles = set()
    collected = []

    for query in QUERIES:
        url = GOOGLE_NEWS_RSS_TEMPLATE.format(query=query)
        feed = feedparser.parse(url)

        for entry in feed.entries:
            title = getattr(entry, "title", "").strip()
            link = getattr(entry, "link", "").strip()
            published_raw = getattr(entry, "published", "") or getattr(entry, "updated", "")
            summary_raw = getattr(entry, "summary", "")

            if not title or not link:
                continue

            published_dt = parse_to_utc(published_raw)
            if published_dt is None or published_dt < cutoff:
                continue

            summary = strip_html(summary_raw)

            if not is_relevant(title, summary):
                continue

            dedup_key = title.lower()
            if dedup_key in seen_titles:
                continue
            seen_titles.add(dedup_key)

            collected.append(
                {
                    "title": title,
                    "link": link,
                    "date": published_dt.isoformat(),
                    "summary": summary,
                }
            )

    collected.sort(key=lambda item: item["date"], reverse=True)
    return collected[:MAX_RESULTS]


def main():
    articles = fetch_entries()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)

    print(f"DONE: Saved {len(articles)} articles to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
