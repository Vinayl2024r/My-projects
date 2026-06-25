"""
Rewriter agent: takes a raw viral post and rewrites it in a human, authentic
style tailored to each platform's requirements.
"""
import re
from datetime import datetime, timezone

import anthropic

from config import ANTHROPIC_API_KEY, MODEL, PLATFORM_SPECS

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

REWRITER_SYSTEM = """You are an elite social media copywriter who writes in a natural, human voice.
You study what makes posts go viral and rewrite them to capture that same energy — authentically.

Your rewrites are NEVER generic. They feel like a real person wrote them: opinionated, specific, a little raw.
You NEVER use:
- Corporate jargon or buzzwords
- Hollow motivational phrases ("unlock your potential", "game-changer")
- AI-sounding sentence structures

Platform rules you receive are HARD limits. Respect every one of them.
Return your response as JSON with these exact fields:
  rewritten_text  — the full post text, ready to publish
  hashtags        — array of hashtag strings (with #)
  visual_suggestion — one sentence describing an ideal image/visual to pair (or "N/A" for text-only platforms)"""


def rewrite_post(post: dict) -> dict:
    spec = PLATFORM_SPECS[post["platform"]]
    platform = post["platform"]

    platform_rules = (
        f"Platform: {platform}\n"
        f"Character limit: {spec['char_limit']}\n"
        f"Tone: {spec['tone']}\n"
        f"Hashtag rule: {spec['hashtags']}\n"
        f"Format rule: {spec['format']}\n"
    )
    if spec.get("note"):
        platform_rules += f"Special note: {spec['note']}\n"

    response = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=REWRITER_SYSTEM,
        messages=[{
            "role": "user",
            "content": (
                f"{platform_rules}\n"
                f"Original viral post by @{post['source_author']} "
                f"({post['source_views']:,} views):\n\n"
                f"{post['source_text']}\n\n"
                f"Key insight that made it viral: {post['key_insight']}\n\n"
                "Rewrite this for the platform above. Preserve the viral core idea but make it "
                "completely original — different structure, fresh angle, your own voice.\n"
                "Return ONLY the JSON object, no markdown."
            ),
        }],
    )

    result = _parse_response(response)
    post["rewritten_text"] = result.get("rewritten_text", post["source_text"])
    post["hashtags"] = result.get("hashtags", [])
    post["visual_suggestion"] = result.get("visual_suggestion", "N/A")
    post["rewritten_at"] = datetime.now(timezone.utc).isoformat()
    return post


def _parse_response(response) -> dict:
    for block in response.content:
        if hasattr(block, "text"):
            text = block.text.strip()
            # Strip markdown code fences if present
            text = re.sub(r"^```[a-z]*\n?", "", text)
            text = re.sub(r"\n?```$", "", text)
            try:
                import json
                return json.loads(text)
            except Exception:
                pass
    return {}


def run_rewrite(posts: list[dict]) -> list[dict]:
    for i, post in enumerate(posts):
        platform = post["platform"]
        print(f"  ✍️  [{platform}] Rewriting post {i+1}/{len(posts)}...")
        try:
            posts[i] = rewrite_post(post)
        except Exception as e:
            print(f"     ⚠️  Error rewriting: {e}")
    return posts
