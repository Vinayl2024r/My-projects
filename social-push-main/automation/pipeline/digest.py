"""
Digest generator: produces a self-contained HTML review page the user opens
locally to review, approve, or reject each post before it goes live.
Also sends the file as an email attachment if EMAIL_CONFIG is configured.
"""
import smtplib
import textwrap
from datetime import date
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from config import EMAIL_CONFIG, STATE_DIR


BADGE_COLORS = {
    "approve":       ("#16a34a", "✅ APPROVE"),
    "revise":        ("#d97706", "⚠️ REVISE"),
    "reject":        ("#dc2626", "❌ REJECT"),
    "auto_rejected": ("#6b7280", "🚫 AUTO-REJECTED"),
    "pending":       ("#6b7280", "⏳ PENDING"),
}

PLATFORM_ICONS = {
    "linkedin":  "🔵", "twitter": "🐦", "instagram": "📸",
    "facebook":  "📘", "threads": "🧵", "youtube":   "▶️", "whatsapp": "💬",
}


def _score_bar(score: float) -> str:
    filled = round(score)
    return "█" * filled + "░" * (10 - filled) + f"  {score:.1f}/10"


def _post_card(post: dict, idx: int) -> str:
    platform = post["platform"]
    icon = PLATFORM_ICONS.get(platform, "🌐")
    audit = post.get("audit") or {}
    rec = audit.get("recommendation", "pending")
    approval_status = post["approval"]["status"]

    badge_color, badge_label = BADGE_COLORS.get(rec, ("#6b7280", rec.upper()))
    if approval_status == "auto_rejected":
        badge_color, badge_label = BADGE_COLORS["auto_rejected"]

    rewritten = post.get("rewritten_text", "").replace("<", "&lt;").replace(">", "&gt;")
    source = post.get("source_text", "").replace("<", "&lt;").replace(">", "&gt;")
    hashtags = " ".join(post.get("hashtags", []))
    visual = post.get("visual_suggestion", "N/A")
    red_flags = audit.get("red_flags", [])
    feedback = audit.get("feedback", "")

    approve_cmd = f"python main.py --approve {post['id']}"
    reject_cmd  = f"python main.py --reject  {post['id']} --note \"your reason\""

    return textwrap.dedent(f"""
    <div class="card" id="{post['id']}">
      <div class="card-header">
        <span class="platform">{icon} {platform.capitalize()}</span>
        <span class="badge" style="background:{badge_color}">{badge_label}</span>
        <span class="views">👁 {post['source_views']:,} views source</span>
      </div>

      <div class="section-label">📝 Rewritten Post</div>
      <div class="post-text">{rewritten}</div>
      <div class="hashtags">{hashtags}</div>
      {"<div class='visual-tip'>🖼 Visual: " + visual + "</div>" if visual != "N/A" else ""}

      <div class="section-label">🔬 PhD Audit  (Dr. Maya Patel)</div>
      <table class="audit-table">
        <tr><td>Accuracy</td>      <td><code>{_score_bar(audit.get('accuracy',0))}</code></td></tr>
        <tr><td>Credibility</td>   <td><code>{_score_bar(audit.get('credibility',0))}</code></td></tr>
        <tr><td>Originality</td>   <td><code>{_score_bar(audit.get('originality',0))}</code></td></tr>
        <tr><td>Engagement</td>    <td><code>{_score_bar(audit.get('engagement',0))}</code></td></tr>
        <tr><td>Brand Safety</td>  <td><code>{_score_bar(audit.get('brand_safety',0))}</code></td></tr>
        <tr class="total-row"><td><b>Overall</b></td><td><code><b>{_score_bar(audit.get('overall_score',0))}</b></code></td></tr>
      </table>
      {"<div class='red-flags'>🚨 Red flags: " + " | ".join(red_flags) + "</div>" if red_flags else ""}
      <div class="feedback">💬 {feedback}</div>

      <details class="source-collapse">
        <summary>📌 Original viral source</summary>
        <div class="source-text">{source}</div>
        <div class="source-meta">— @{post['source_author']} · <a href="{post['source_url']}" target="_blank">{post['source_url']}</a></div>
      </details>

      <div class="actions">
        <div class="action-label">Run in terminal to approve or reject:</div>
        <code class="cmd approve-cmd">{approve_cmd}</code>
        <code class="cmd reject-cmd">{reject_cmd}</code>
      </div>
    </div>
    """)


def generate(posts: list[dict], output_dir: Path = STATE_DIR) -> Path:
    today = date.today().isoformat()
    cards_html = "\n".join(_post_card(p, i) for i, p in enumerate(posts))

    approve_all = " ".join(p["id"] for p in posts if p["audit"] and p["audit"].get("recommendation") == "approve")
    summary = {
        "total": len(posts),
        "approve": sum(1 for p in posts if p.get("audit", {}).get("recommendation") == "approve"),
        "revise":  sum(1 for p in posts if p.get("audit", {}).get("recommendation") == "revise"),
        "reject":  sum(1 for p in posts if p.get("audit", {}).get("recommendation") == "reject"),
    }

    html = textwrap.dedent(f"""<!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>Social Agent Daily Digest — {today}</title>
      <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
                background: #0f172a; color: #e2e8f0; padding: 24px; }}
        h1 {{ font-size: 1.6rem; margin-bottom: 4px; color: #f8fafc; }}
        .subtitle {{ color: #94a3b8; margin-bottom: 24px; font-size: .9rem; }}
        .summary {{ display: flex; gap: 12px; margin-bottom: 28px; flex-wrap: wrap; }}
        .summary-chip {{ padding: 6px 14px; border-radius: 20px; font-size: .85rem; font-weight: 600; }}
        .chip-total   {{ background:#1e293b; color:#94a3b8; }}
        .chip-approve {{ background:#14532d; color:#86efac; }}
        .chip-revise  {{ background:#451a03; color:#fcd34d; }}
        .chip-reject  {{ background:#450a0a; color:#fca5a5; }}
        .bulk-cmd {{ background:#1e293b; border: 1px solid #334155; border-radius:8px;
                     padding:12px 16px; margin-bottom:28px; font-size:.85rem; }}
        .bulk-cmd code {{ color:#7dd3fc; }}
        .card {{ background:#1e293b; border:1px solid #334155; border-radius:12px;
                 padding:20px; margin-bottom:20px; }}
        .card-header {{ display:flex; align-items:center; gap:12px; margin-bottom:16px; flex-wrap:wrap; }}
        .platform {{ font-size:1rem; font-weight:700; color:#f1f5f9; text-transform:capitalize; }}
        .badge {{ padding:3px 10px; border-radius:12px; font-size:.78rem; font-weight:700; color:#fff; }}
        .views {{ color:#64748b; font-size:.82rem; margin-left:auto; }}
        .section-label {{ font-size:.75rem; font-weight:700; text-transform:uppercase;
                           color:#64748b; letter-spacing:.08em; margin:14px 0 6px; }}
        .post-text {{ background:#0f172a; border-radius:8px; padding:12px;
                      white-space:pre-wrap; font-size:.9rem; line-height:1.6; color:#cbd5e1; }}
        .hashtags {{ color:#38bdf8; font-size:.82rem; margin-top:6px; }}
        .visual-tip {{ color:#a78bfa; font-size:.82rem; margin-top:4px; }}
        .audit-table {{ width:100%; border-collapse:collapse; margin-top:6px; }}
        .audit-table td {{ padding:5px 8px; font-size:.82rem; border-bottom:1px solid #1e293b; }}
        .audit-table td:first-child {{ color:#94a3b8; width:110px; }}
        .audit-table code {{ font-family:"SF Mono","Consolas",monospace; color:#67e8f9; font-size:.78rem; }}
        .total-row td {{ color:#f1f5f9 !important; border-bottom:none; padding-top:8px; }}
        .red-flags {{ background:#450a0a; color:#fca5a5; border-radius:6px;
                      padding:8px 12px; margin-top:10px; font-size:.82rem; }}
        .feedback {{ color:#94a3b8; font-size:.85rem; margin-top:10px; font-style:italic; line-height:1.5; }}
        .source-collapse {{ margin-top:14px; }}
        .source-collapse summary {{ cursor:pointer; color:#64748b; font-size:.82rem; }}
        .source-text {{ background:#0f172a; border-radius:6px; padding:10px; margin-top:8px;
                        white-space:pre-wrap; font-size:.8rem; color:#64748b; }}
        .source-meta {{ color:#475569; font-size:.78rem; margin-top:6px; }}
        .source-meta a {{ color:#38bdf8; }}
        .actions {{ margin-top:16px; border-top:1px solid #334155; padding-top:14px; }}
        .action-label {{ color:#64748b; font-size:.78rem; margin-bottom:8px; }}
        .cmd {{ display:block; font-family:"SF Mono","Consolas",monospace; font-size:.8rem;
                padding:8px 12px; border-radius:6px; margin-bottom:6px; word-break:break-all; }}
        .approve-cmd {{ background:#14532d; color:#86efac; }}
        .reject-cmd  {{ background:#1c1917; color:#9ca3af; }}
      </style>
    </head>
    <body>
      <h1>📡 Social Agent Daily Digest</h1>
      <div class="subtitle">{today} · Generated by Viral Social Agent</div>

      <div class="summary">
        <span class="summary-chip chip-total">📋 {summary['total']} posts</span>
        <span class="summary-chip chip-approve">✅ {summary['approve']} approve</span>
        <span class="summary-chip chip-revise">⚠️ {summary['revise']} revise</span>
        <span class="summary-chip chip-reject">❌ {summary['reject']} reject</span>
      </div>

      <div class="bulk-cmd">
        <b>Approve all recommended posts at once:</b><br>
        <code>python main.py --approve {approve_all}</code>
      </div>

      {cards_html}
    </body>
    </html>
    """)

    out_path = output_dir / f"digest_{today}.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"  📄 Digest saved → {out_path}")
    return out_path


def send_email(digest_path: Path) -> bool:
    cfg = EMAIL_CONFIG
    if not all([cfg["from_email"], cfg["to_email"], cfg["password"]]):
        print("  📧 Email not configured — skipping (open the HTML file directly)")
        return False

    today = date.today().isoformat()
    msg = MIMEMultipart()
    msg["Subject"] = f"📡 Social Agent Digest — {today}"
    msg["From"] = cfg["from_email"]
    msg["To"] = cfg["to_email"]

    body = MIMEText(
        f"Your daily viral content digest is attached.\n\n"
        f"Open digest_{today}.html in a browser to review and approve posts.\n\n"
        f"Then run:\n  python main.py --post\n\nto publish approved content.",
        "plain",
    )
    msg.attach(body)

    with open(digest_path, "rb") as f:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", f"attachment; filename={digest_path.name}")
    msg.attach(part)

    try:
        with smtplib.SMTP(cfg["smtp_server"], cfg["smtp_port"]) as s:
            s.starttls()
            s.login(cfg["from_email"], cfg["password"])
            s.sendmail(cfg["from_email"], cfg["to_email"], msg.as_string())
        print(f"  📧 Digest emailed to {cfg['to_email']}")
        return True
    except Exception as e:
        print(f"  ⚠️  Email failed: {e}")
        return False
