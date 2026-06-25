import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
STATE_DIR = BASE_DIR / "state"
TEMPLATES_DIR = BASE_DIR / "templates"
SKILLS_DIR = BASE_DIR.parent / "skills" / "social-push" / "references"
STATE_DIR.mkdir(exist_ok=True)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MODEL = "claude-sonnet-4-6"

# Topics to research viral posts about (edit freely)
RESEARCH_TOPICS = [
    "AI agents vs SaaS",
]

POSTS_PER_PLATFORM = 3  # 1-3 viral posts to find per platform

DAILY_RUN_TIME = os.getenv("DAILY_RUN_TIME", "06:00")

# Email (optional — digest is also saved as HTML file)
EMAIL_CONFIG = {
    "smtp_server": os.getenv("SMTP_SERVER", "smtp.gmail.com"),
    "smtp_port":   int(os.getenv("SMTP_PORT", "587")),
    "from_email":  os.getenv("EMAIL_FROM", ""),
    "to_email":    os.getenv("EMAIL_TO", ""),
    "password":    os.getenv("EMAIL_PASSWORD", ""),
}

# Per-platform requirements used by rewriter, auditor, and poster
PLATFORM_SPECS: dict[str, dict] = {
    "linkedin": {
        "char_limit": 3000,
        "tone": "professional, insightful, first-person narrative, thought-leadership",
        "hashtags": "3–5 at the very end",
        "format": "short paragraphs separated by blank lines, no markdown bullets, hook in first line",
        "supports_auto_post": True,
        "workflow_ref": str(SKILLS_DIR / "LinkedIn帖子.md"),
        "session_name": "linkedin",
    },
    "twitter": {
        "char_limit": 280,
        "tone": "punchy, opinionated, witty, conversational",
        "hashtags": "1–2 embedded in text",
        "format": "single tweet OR numbered thread (1/ 2/ 3/) — choose thread when depth is needed",
        "supports_auto_post": True,
        "workflow_ref": str(SKILLS_DIR / "X推文.md"),
        "session_name": "twitter",
    },
    "instagram": {
        "char_limit": 2200,
        "tone": "aspirational, personal, visual-forward",
        "hashtags": "15–20 at the end on separate lines",
        "format": "hook in first sentence (visible before 'more'), short punchy lines, CTA last",
        "supports_auto_post": True,
        "workflow_ref": None,
        "session_name": "instagram",
        "note": "Caption assumes an accompanying image. Suggest a visual concept in brackets.",
    },
    "facebook": {
        "char_limit": 63206,
        "tone": "warm, community-focused, conversational storytelling",
        "hashtags": "2–3 max",
        "format": "paragraph style, longer form OK, emotionally resonant opener",
        "supports_auto_post": True,
        "workflow_ref": None,
        "session_name": "facebook",
    },
    "threads": {
        "char_limit": 500,
        "tone": "casual, raw, authentic, like texting a sharp friend",
        "hashtags": "1–2 max or none",
        "format": "short post or mini-thread — punchy, no fluff",
        "supports_auto_post": True,
        "workflow_ref": None,
        "session_name": "threads",
    },
    "youtube": {
        "char_limit": 5000,
        "tone": "engaging, educational, SEO-aware",
        "hashtags": "5–10 in description",
        "format": "video script outline + SEO-optimised description. No actual video produced.",
        "supports_auto_post": False,
        "skip_reason": "YouTube requires video content. Script and description provided for manual upload.",
        "session_name": None,
    },
    "whatsapp": {
        "char_limit": 65536,
        "tone": "personal, direct, forward-able by anyone",
        "hashtags": "none",
        "format": "plain text, emojis OK, no formatting, no links required",
        "supports_auto_post": False,
        "skip_reason": "WhatsApp posting requires WhatsApp Business API. Message draft provided.",
        "session_name": None,
    },
}

PLATFORMS = list(PLATFORM_SPECS.keys())
