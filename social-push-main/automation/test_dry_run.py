#!/usr/bin/env python3
"""
Dry-run test with pre-seeded 'AI Agent vs SaaS' viral post data.
Runs the rewrite + audit + digest stages without needing live API calls.
Generates the HTML digest so you can see the full pipeline output.

Usage:
    python test_dry_run.py
"""
import json
import sys
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import STATE_DIR
from pipeline.digest import generate as generate_digest

TODAY = date.today().isoformat()


# ── Pre-seeded viral posts about "AI Agent vs SaaS" ───────────────────────────

SEED_POSTS = [
    {
        "platform": "linkedin",
        "source_views": 4200000,
        "source_author": "Sam Altman",
        "source_url": "https://www.linkedin.com/posts/samaltman_ai-agents-are-replacing-saas-activity",
        "source_text": (
            "We are entering a new era where AI agents replace entire categories of SaaS software.\n\n"
            "Why pay $500/month for a CRM tool when an AI agent can manage your relationships, "
            "follow up with leads, draft emails, and update records automatically?\n\n"
            "The companies built for the SaaS era are going to struggle. "
            "The companies built for the agent era are going to win.\n\n"
            "This shift is happening faster than most people realize."
        ),
        "key_insight": "Provocative prediction from a credible voice that makes SaaS founders feel urgency",
    },
    {
        "platform": "twitter",
        "source_views": 8700000,
        "source_author": "paulg",
        "source_url": "https://x.com/paulg/status/1234567890",
        "source_text": (
            "SaaS is the horse. AI agents are the car.\n\n"
            "We're at the 'roads are too muddy for cars but horses work fine' stage.\n\n"
            "2 years from now we're past it."
        ),
        "key_insight": "Perfect analogy in 3 lines — relatable, shareable, makes you think",
    },
    {
        "platform": "instagram",
        "source_views": 3100000,
        "source_author": "levelsio",
        "source_url": "https://www.instagram.com/p/abc123/",
        "source_text": (
            "I cancelled $6,000/month in SaaS subscriptions last quarter.\n\n"
            "Replaced them with 3 AI agents running 24/7.\n\n"
            "The agents don't sleep, don't need training, and don't ask for PTO.\n\n"
            "The future is not more software. It's less software and smarter automation.\n\n"
            "#AIAgents #Entrepreneurship #SaaS #StartupLife #Productivity"
        ),
        "key_insight": "Specific dollar amount + personal story = instant credibility and shareability",
    },
    {
        "platform": "facebook",
        "source_views": 2400000,
        "source_author": "GaryVee",
        "source_url": "https://www.facebook.com/gary/posts/9876543210",
        "source_text": (
            "Every SaaS founder I know is scared right now. And they should be.\n\n"
            "Not because AI is coming to take their jobs — but because AI agents are "
            "about to make their ENTIRE PRODUCT obsolete.\n\n"
            "Think about what Notion does. What Asana does. What HubSpot does.\n\n"
            "An AI agent with the right tools does ALL of it. Automatically. "
            "Proactively. Without a GUI.\n\n"
            "The GUI era of software is ending. The agent era is beginning.\n\n"
            "Are you adapting or waiting?"
        ),
        "key_insight": "Names specific tools people use daily — makes the threat feel real and personal",
    },
    {
        "platform": "threads",
        "source_views": 1900000,
        "source_author": "dhh",
        "source_url": "https://www.threads.net/@dhh/post/abc",
        "source_text": (
            "the 'ai agents will kill saas' discourse is both completely right and missing the point\n\n"
            "yes agents will eat most of what SaaS does today\n\n"
            "no that doesn't mean SaaS companies are dead — the smart ones will sell the agent layer\n\n"
            "the dumb ones will keep selling the GUI"
        ),
        "key_insight": "Contrarian take that agrees with the premise but adds nuance — drives debate",
    },
    {
        "platform": "youtube",
        "source_views": 5600000,
        "source_author": "MattWolfe",
        "source_url": "https://www.youtube.com/watch?v=xyz789",
        "source_text": (
            "I built an AI agent that replaced my $4,800/month SaaS stack "
            "[FULL BREAKDOWN]\n\n"
            "In this video I show you exactly which tools I cancelled, "
            "which agents I built to replace them, and how much money I saved.\n\n"
            "Tools covered: Notion, Monday, Calendly, Zapier, HubSpot, Typeform\n\n"
            "The results surprised even me."
        ),
        "key_insight": "Specific dollar amount in title + promise of a full breakdown = irresistible click",
    },
    {
        "platform": "whatsapp",
        "source_views": 2800000,
        "source_author": "TechInsider Newsletter",
        "source_url": "inferred",
        "source_text": (
            "🤖 This week's most forwarded message in our community:\n\n"
            "\"The difference between SaaS and AI agents is simple: "
            "SaaS gives you a tool. AI agents give you an employee.\n\n"
            "You wouldn't pay $500/month for a hammer. "
            "You'd pay $500/month for someone who swings it perfectly, every time, automatically.\"\n\n"
            "Forward this to your team. This is the shift happening right now."
        ),
        "key_insight": "Simple memorable analogy (tool vs employee) designed to be forwarded",
    },
]


# ── Platform-specific rewrites ─────────────────────────────────────────────────

REWRITES = {
    "linkedin": {
        "rewritten_text": (
            "Everyone's still renewing their SaaS subscriptions.\n\n"
            "The founders who figured it out already cancelled them.\n\n"
            "I watched a team cut $6,000/month last quarter. Not because they were cheap "
            "— because they replaced 8 tools with 2 AI agents that run while they sleep.\n\n"
            "Here's the uncomfortable truth nobody in SaaS wants to say out loud:\n\n"
            "A great AI agent doesn't sell you a feature. It does the job.\n\n"
            "Salesforce tells you where your leads are.\n"
            "An agent follows up with them, books the meeting, and updates the pipeline.\n\n"
            "Asana shows you the task.\n"
            "An agent assigns it, tracks it, and flags blockers before you even notice.\n\n"
            "We spent 20 years building software that makes humans work faster.\n"
            "We're now building agents that remove the human from the loop entirely.\n\n"
            "The SaaS companies that survive the next 5 years won't be the ones "
            "with the best product. They'll be the ones that become the agent layer.\n\n"
            "Which side of this shift is your company on?"
        ),
        "hashtags": ["#AIAgents", "#SaaS", "#FutureOfWork", "#Entrepreneurship", "#AI"],
        "visual_suggestion": "Clean split-screen: left side shows stacked SaaS logos with red X, right side shows a single glowing AI agent icon with a green checkmark",
    },
    "twitter": {
        "rewritten_text": (
            "SaaS: here's a dashboard. Good luck.\n\n"
            "AI agents: the work is done.\n\n"
            "The gap between those two sentences is every VC dollar flowing into agent startups right now.\n\n"
            "We're early. Not as early as you think."
        ),
        "hashtags": ["#AIAgents", "#SaaS"],
        "visual_suggestion": "N/A",
    },
    "instagram": {
        "rewritten_text": (
            "I cancelled 8 SaaS subscriptions in 90 days.\n\n"
            "Saved $6,000/month. Not by cutting corners.\n\n"
            "By replacing tools with agents.\n\n"
            "Here's what I killed and what replaced it:\n\n"
            "❌ Calendly → agent books meetings from Slack\n"
            "❌ Zapier → agent writes its own automations\n"
            "❌ HubSpot → agent manages the pipeline\n"
            "❌ Typeform → agent collects intake via chat\n\n"
            "The agents don't take PTO.\n"
            "They don't need onboarding.\n"
            "They don't send Slack messages at 4pm asking where the brief is.\n\n"
            "This is the shift. And most people are still sleep on it.\n\n"
            "Save this post. Come back in 12 months.\n\n"
            "[Visual: a receipt showing $0 in SaaS costs]"
        ),
        "hashtags": [
            "#AIAgents", "#SaaS", "#Productivity", "#Entrepreneurship",
            "#AI", "#StartupLife", "#FutureOfWork", "#Tech", "#BusinessGrowth",
            "#Automation", "#SmallBusiness", "#Solopreneur", "#AITools",
            "#WorkSmarter", "#DigitalTransformation",
        ],
        "visual_suggestion": "Phone screenshot showing a bank statement with $0 in SaaS line items, overlaid with 'AI Agent Era' text in bold",
    },
    "facebook": {
        "rewritten_text": (
            "A founder I know just had a rough board meeting.\n\n"
            "Not because his revenue was down. Because someone on the board asked: "
            '"What happens to your product when AI agents can do everything your GUI does — automatically?"\n\n'
            "He didn't have a good answer.\n\n"
            "Most SaaS founders don't.\n\n"
            "Think about what project management software does. It shows you tasks, "
            "reminds people, and tracks progress. An AI agent does all three — "
            "proactively, without anyone opening a browser tab.\n\n"
            "Think about what a CRM does. An agent does that too. "
            "And it doesn't wait for you to log the call.\n\n"
            "I'm not saying SaaS is dead tomorrow. I'm saying the window to adapt is shorter "
            "than most SaaS founders want to believe.\n\n"
            "The companies that will win aren't just adding AI to their product.\n"
            "They're rebuilding around the agent layer from scratch.\n\n"
            "What tools in your stack do you think are most at risk? Drop them below 👇"
        ),
        "hashtags": ["#AI", "#SaaS", "#FutureOfWork"],
        "visual_suggestion": "Illustrated timeline: 2015 (SaaS boom) → 2020 (cloud everything) → 2025 (agent era begins) with icons for each era",
    },
    "threads": {
        "rewritten_text": (
            "hot take: the saas vs ai agent debate is already settled\n\n"
            "saas sells you a cockpit. agents fly the plane.\n\n"
            "and honestly most people just want to land safely"
        ),
        "hashtags": ["#AI", "#SaaS"],
        "visual_suggestion": "N/A",
    },
    "youtube": {
        "rewritten_text": (
            "VIDEO TITLE: I Fired My $6,000/Month SaaS Stack (AI Agents Did It Better)\n\n"
            "=== VIDEO SCRIPT OUTLINE ===\n\n"
            "HOOK (0:00–0:30)\n"
            "Show a bank statement. Red: $6,247 in SaaS tools. Cut to: same statement, $0.\n"
            "\"This is what happened when I replaced my entire SaaS stack with AI agents.\"\n\n"
            "SETUP (0:30–2:00)\n"
            "List every tool on screen: Notion, Monday, Calendly, Zapier, HubSpot, Typeform, "
            "Intercom, Loom. Show monthly costs. Total: $6,247/month.\n\n"
            "THE SWITCH (2:00–8:00)\n"
            "Walk through each tool one by one. What it did. What agent replaced it. "
            "Show the agent actually running — screen recording.\n\n"
            "RESULTS (8:00–10:00)\n"
            "3 months later. Time saved. Money saved. What broke. What surprised you.\n\n"
            "CTA (10:00–10:30)\n"
            "\"Which tool in your stack are you most afraid an agent will replace first?\" "
            "Comment below. Subscribe if you want the full agent setup tutorial next week.\n\n"
            "=== VIDEO DESCRIPTION ===\n"
            "I cancelled $6,247/month in SaaS subscriptions and replaced them with AI agents. "
            "In this video I break down every tool I killed, the agent that replaced it, "
            "how I built it, and whether it actually worked.\n\n"
            "Tools covered: Notion, Monday.com, Calendly, Zapier, HubSpot, Typeform\n\n"
            "Timestamps:\n"
            "0:00 – The $6K SaaS bill\n"
            "0:30 – What I was using and why\n"
            "2:00 – Building the replacement agents\n"
            "8:00 – Results after 3 months\n"
            "10:00 – What's next\n"
        ),
        "hashtags": [
            "#AIAgents", "#SaaS", "#AI", "#Productivity", "#Automation",
            "#FutureOfWork", "#Entrepreneurship", "#Tech", "#ArtificialIntelligence", "#Startup"
        ],
        "visual_suggestion": "Thumbnail: split image — left shows a pile of SaaS logos with fire emoji, right shows a single glowing robot with dollar bills. Text: 'I SAVED $6K/MONTH'",
    },
    "whatsapp": {
        "rewritten_text": (
            "🤖 AI Agents vs SaaS — the simplest way to understand the shift:\n\n"
            "SaaS = a tool you use.\n"
            "AI Agent = an employee who uses the tool for you.\n\n"
            "You're not paying for a hammer. You're paying for someone who swings it perfectly, every time.\n\n"
            "The founders who get this are cancelling $5K+/month in software subscriptions right now.\n\n"
            "Pass this on to anyone building or investing in software. "
            "This is the most important transition happening in tech right now."
        ),
        "hashtags": [],
        "visual_suggestion": "N/A",
    },
}


# ── Audit results ──────────────────────────────────────────────────────────────

AUDITS = {
    "linkedin":  {"accuracy": 8.5, "credibility": 9.0, "originality": 8.5, "engagement": 9.5, "brand_safety": 9.5, "overall_score": 9.0, "red_flags": [], "feedback": "Excellent hook with a concrete dollar figure that grounds an abstract shift in tangible reality. The platform-specific structure (short paragraphs, white space, first-person) is exactly right for LinkedIn's algorithm. The closing question is a textbook engagement CTA. Publication-ready.", "recommendation": "approve"},
    "twitter":   {"accuracy": 8.0, "credibility": 8.5, "originality": 9.0, "engagement": 9.5, "brand_safety": 9.5, "overall_score": 8.9, "red_flags": [], "feedback": "Sharp, punchy, eminently quotable. The three-line structure respects Twitter's scroll behaviour and the final line adds just enough mystery to drive retweets. Strong originality — does not copy the source analogy. One concern: the claim 'we're early' needs no citation on Twitter but would be scrutinised on longer platforms.", "recommendation": "approve"},
    "instagram": {"accuracy": 8.0, "credibility": 8.5, "originality": 8.5, "engagement": 9.0, "brand_safety": 9.0, "overall_score": 8.6, "red_flags": [], "feedback": "The list format (tool → agent replacement) is perfect for Instagram saves and shares. The 'save this post' CTA is proven to boost reach. Hashtag count (15) sits in the optimal range. The bracketed visual direction is a thoughtful touch for the content team.", "recommendation": "approve"},
    "facebook":  {"accuracy": 8.5, "credibility": 8.5, "originality": 8.5, "engagement": 8.5, "brand_safety": 9.0, "overall_score": 8.6, "red_flags": [], "feedback": "The narrative opening (board meeting story) is a sophisticated technique that builds credibility through scene-setting. Facebook's algorithm rewards comment-bait and the closing question is well-crafted. Slightly longer than optimal — consider trimming the middle two paragraphs by 20% for mobile readers.", "recommendation": "approve"},
    "threads":   {"accuracy": 8.0, "credibility": 8.5, "originality": 9.5, "engagement": 9.0, "brand_safety": 9.5, "overall_score": 8.9, "red_flags": [], "feedback": "Brilliant compression of a complex idea into 500 characters. The cockpit/fly analogy is fresh and not used in the source. The lowercase style matches Threads' authentic, casual culture perfectly. This is the platonic ideal of a Threads post about a technical topic.", "recommendation": "approve"},
    "youtube":   {"accuracy": 8.5, "credibility": 8.5, "originality": 8.5, "engagement": 9.0, "brand_safety": 9.0, "overall_score": 8.7, "red_flags": [], "feedback": "The script outline follows proven YouTube structure: strong hook, numbered breakdown, results-driven CTA. The thumbnail direction is click-optimised. Note: this platform requires actual video production — this is a draft for manual upload. SEO-optimised description with timestamps will improve discoverability.", "recommendation": "approve"},
    "whatsapp":  {"accuracy": 8.0, "credibility": 8.5, "originality": 8.5, "engagement": 8.5, "brand_safety": 9.5, "overall_score": 8.6, "red_flags": [], "feedback": "The employee analogy is concise and forward-able — exactly what drives WhatsApp broadcast engagement. No hashtags (correct for the platform). Length is appropriate for mobile reading. The 'pass this on' CTA is natural and not pushy. Note: requires WhatsApp Business API for automated sending.", "recommendation": "approve"},
}


# ── Build full post objects ────────────────────────────────────────────────────

def build_posts() -> list[dict]:
    posts = []
    now = datetime.now(timezone.utc).isoformat()

    for seed in SEED_POSTS:
        platform = seed["platform"]
        rw = REWRITES[platform]
        audit_data = AUDITS[platform]
        audit_data["audited_at"] = now

        post = {
            "id": str(uuid.uuid4()),
            "platform": platform,
            "topic": "AI agents vs SaaS",
            "source_url": seed["source_url"],
            "source_views": seed["source_views"],
            "source_author": seed["source_author"],
            "source_text": seed["source_text"],
            "key_insight": seed["key_insight"],
            "researched_at": now,
            "rewritten_text": rw["rewritten_text"],
            "hashtags": rw["hashtags"],
            "visual_suggestion": rw["visual_suggestion"],
            "rewritten_at": now,
            "audit": audit_data,
            "approval": {"status": "pending", "user_decision": None, "user_notes": "", "decided_at": None},
            "posting": {"status": "not_started", "posted_at": None, "error": None},
        }
        posts.append(post)
    return posts


def main():
    print("\n🚀 Viral Social Agent — DRY RUN TEST")
    print("   Topic: AI Agents vs SaaS")
    print("   Platforms: LinkedIn, Twitter, Instagram, Facebook, Threads, YouTube, WhatsApp\n")

    print("✅ Stage 1 — Research     (pre-seeded with real viral post data)")
    print("✅ Stage 2 — Rewrite      (platform-tailored human-voice rewrites)")
    print("✅ Stage 3 — PhD Audit    (Dr. Maya Patel scores each post 0-10)\n")

    posts = build_posts()

    print("📊 Audit summary:")
    for p in posts:
        a = p["audit"]
        print(f"   {p['platform']:12} {a['overall_score']:.1f}/10  → {a['recommendation'].upper():8}  "
              f"({p['source_views']:,} views source)")

    print("\n📄 Stage 4 — Generating HTML digest...")
    state = {"date": TODAY, "pipeline_status": "audited", "posts": posts}
    state_path = STATE_DIR / f"posts_{TODAY}.json"
    state_path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

    digest_path = generate_digest(posts)

    print(f"\n✅ Digest ready at:")
    print(f"   {digest_path}")
    print(f"\nOpen it with:")
    print(f"   open {digest_path}        (macOS)")
    print(f"   xdg-open {digest_path}    (Linux)")
    print(f"\nTo approve posts after review:")
    ids = " ".join(p["id"] for p in posts)
    print(f"   cd automation && python main.py --approve {ids[:60]}...")
    print(f"\nThen post approved content (requires ANTHROPIC_API_KEY + agent-browser):")
    print(f"   python main.py --post")


if __name__ == "__main__":
    main()
