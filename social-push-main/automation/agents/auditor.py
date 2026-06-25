"""
Auditor agent: a PhD-level expert persona that reviews each rewritten post
for accuracy, credibility, originality, engagement potential, and safety.
"""
import json
import re
from datetime import datetime, timezone

import anthropic

from config import ANTHROPIC_API_KEY, MODEL

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

AUDITOR_SYSTEM = """You are Dr. Maya Patel — a PhD in Communication Studies and Computational Social Science
with 18 years reviewing viral content for major media organisations.

You audit social media posts with the rigour of an academic peer reviewer and the instincts of a seasoned editor.

For every post, score these five dimensions from 0–10:
  accuracy           — are all factual claims verifiable? flag misinformation.
  credibility        — does this feel trustworthy? no sensationalism or misleading framing.
  originality        — is the rewrite sufficiently distinct from the source to avoid plagiarism?
  engagement         — hook quality, emotional resonance, CTA, shareability on this platform.
  brand_safety       — no legal issues, hate speech, controversial claims, or reputational risks.

Compute overall_score = average of the five.

recommendation:
  "approve"  — overall_score >= 7.5 AND no red_flags
  "revise"   — overall_score 5–7.4 OR minor red_flags
  "reject"   — overall_score < 5 OR any critical red_flag

Return ONLY a valid JSON object with these exact fields:
{
  "accuracy": <0-10>,
  "credibility": <0-10>,
  "originality": <0-10>,
  "engagement": <0-10>,
  "brand_safety": <0-10>,
  "overall_score": <0-10>,
  "red_flags": ["list any issues, or empty array"],
  "feedback": "2–3 sentence expert commentary",
  "recommendation": "approve" | "revise" | "reject",
  "audited_at": "<ISO timestamp>"
}"""


def audit_post(post: dict) -> dict:
    platform = post["platform"]
    content_to_audit = post["rewritten_text"]
    if post["hashtags"]:
        content_to_audit += "\n\n" + " ".join(post["hashtags"])

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=AUDITOR_SYSTEM,
        messages=[{
            "role": "user",
            "content": (
                f"Platform: {platform}\n"
                f"Source post views: {post['source_views']:,}\n"
                f"Source author: @{post['source_author']}\n\n"
                f"Rewritten post to audit:\n\n{content_to_audit}\n\n"
                "Provide your expert audit. Return ONLY the JSON object."
            ),
        }],
    )

    audit_result = _parse_response(response)
    audit_result["audited_at"] = datetime.now(timezone.utc).isoformat()
    post["audit"] = audit_result

    # Auto-set approval status based on recommendation
    recommendation = audit_result.get("recommendation", "revise")
    if recommendation == "reject":
        post["approval"]["status"] = "auto_rejected"
    return post


def _parse_response(response) -> dict:
    for block in response.content:
        if hasattr(block, "text"):
            text = block.text.strip()
            text = re.sub(r"^```[a-z]*\n?", "", text)
            text = re.sub(r"\n?```$", "", text)
            try:
                return json.loads(text)
            except Exception:
                pass
    return {
        "accuracy": 0, "credibility": 0, "originality": 0,
        "engagement": 0, "brand_safety": 0, "overall_score": 0,
        "red_flags": ["audit_parse_error"], "feedback": "Audit failed to parse.",
        "recommendation": "revise",
    }


def run_audit(posts: list[dict]) -> list[dict]:
    for i, post in enumerate(posts):
        platform = post["platform"]
        print(f"  🔬 [{platform}] Auditing post {i+1}/{len(posts)}...")
        try:
            posts[i] = audit_post(post)
            rec = posts[i]["audit"].get("recommendation", "?")
            score = posts[i]["audit"].get("overall_score", 0)
            print(f"     Score: {score:.1f}/10  →  {rec.upper()}")
        except Exception as e:
            print(f"     ⚠️  Audit error: {e}")
    return posts
