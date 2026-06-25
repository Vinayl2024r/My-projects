"""
Research agent: finds top 1-3 viral posts (1M+ views) per platform using
Claude + web_search_20250305. Falls back to Claude's knowledge if a platform
can't be directly scraped.
"""
import json
import re
import uuid
from datetime import datetime, timezone

import anthropic

from config import ANTHROPIC_API_KEY, MODEL, PLATFORM_SPECS, POSTS_PER_PLATFORM, RESEARCH_TOPICS

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SEARCH_HINTS: dict[str, str] = {
    "linkedin":  'site:linkedin.com "million" OR "viral" post 2026',
    "twitter":   'site:x.com OR site:twitter.com million impressions viral 2026',
    "instagram": 'site:instagram.com reel viral million views 2026',
    "facebook":  'site:facebook.com viral post million views 2026',
    "threads":   'site:threads.net viral trending million 2026',
    "youtube":   'site:youtube.com viral shorts million views 2026',
    "whatsapp":  'whatsapp viral message forwarded millions 2026',
}

RESEARCHER_SYSTEM = """You are an expert viral-content researcher with access to web search.
Your job: find the top {n} most viral posts on {platform} RIGHT NOW (today, 2026).
Target: posts with 1 million+ views, likes, or impressions.

For each post you find, extract exactly:
- source_url: direct URL to the post (or "inferred" if not linkable)
- source_views: numeric estimate of views/impressions (e.g. 2400000)
- source_author: handle or name of the creator
- source_text: the FULL text/caption of the post (copy it verbatim)
- key_insight: ONE sentence on WHY this went viral

Search thoroughly. Use multiple searches if needed.
Return ONLY a valid JSON array — no markdown, no commentary."""


def _run_with_web_search(platform: str, topic: str) -> list[dict]:
    """Run Claude with web_search in an agentic loop; return list of raw post dicts."""
    system = RESEARCHER_SYSTEM.format(n=POSTS_PER_PLATFORM, platform=platform)
    hint = SEARCH_HINTS.get(platform, platform)
    messages: list[dict] = [{
        "role": "user",
        "content": (
            f'Find the top {POSTS_PER_PLATFORM} viral {platform} posts about "{topic}" today.\n'
            f'Search hint: {hint}\n'
            f'Return a JSON array with fields: source_url, source_views, source_author, source_text, key_insight.'
        ),
    }]

    for _ in range(6):  # max 6 tool-call rounds
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=system,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    return _parse_json(block.text, platform, topic)
            return []

        # Continue agentic loop: append assistant turn + acknowledge tool results
        messages.append({"role": "assistant", "content": response.content})
        tool_results = [
            {"type": "tool_result", "tool_use_id": b.id, "content": "done"}
            for b in response.content
            if b.type == "tool_use"
        ]
        if tool_results:
            messages.append({"role": "user", "content": tool_results})
        else:
            break

    return []


def _parse_json(text: str, platform: str, topic: str) -> list[dict]:
    """Extract JSON array from Claude's response."""
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        return []
    try:
        posts = json.loads(match.group())
        return [_normalise(p, platform, topic) for p in posts if isinstance(p, dict)]
    except json.JSONDecodeError:
        return []


def _normalise(raw: dict, platform: str, topic: str) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "platform": platform,
        "topic": topic,
        "source_url": raw.get("source_url", "inferred"),
        "source_views": int(raw.get("source_views", 0)),
        "source_author": raw.get("source_author", "unknown"),
        "source_text": raw.get("source_text", ""),
        "key_insight": raw.get("key_insight", ""),
        "researched_at": datetime.now(timezone.utc).isoformat(),
        # These will be filled by later pipeline stages
        "rewritten_text": "",
        "hashtags": [],
        "visual_suggestion": "",
        "rewritten_at": None,
        "audit": None,
        "approval": {"status": "pending", "user_decision": None, "user_notes": "", "decided_at": None},
        "posting": {"status": "not_started", "posted_at": None, "error": None},
    }


def run_research() -> list[dict]:
    """Research viral posts across all platforms for the configured topics."""
    all_posts: list[dict] = []
    for topic in RESEARCH_TOPICS[:2]:  # research top 2 topics to keep runtime reasonable
        for platform in PLATFORM_SPECS:
            print(f"  🔍 [{platform}] Researching '{topic}'...")
            posts = _run_with_web_search(platform, topic)
            print(f"     Found {len(posts)} post(s)")
            all_posts.extend(posts)
    return all_posts
