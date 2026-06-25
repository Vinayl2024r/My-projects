#!/usr/bin/env python3
"""
Viral Social Agent — CLI Orchestrator
======================================
Full pipeline (daily via --schedule):
  research  →  rewrite  →  audit  →  digest (user reviews)  →  post

Individual stage commands:
  python main.py --research
  python main.py --rewrite
  python main.py --audit
  python main.py --digest
  python main.py --post

Approval (after reviewing the HTML digest):
  python main.py --approve <post_id> [<post_id> ...]
  python main.py --reject  <post_id> --note "reason"

Run full pipeline once (no schedule):
  python main.py --run-once

Run daily on a schedule:
  python main.py --schedule
"""
import argparse
import json
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path

# Make sure config can be imported from this directory
sys.path.insert(0, str(Path(__file__).parent))

from config import DAILY_RUN_TIME, STATE_DIR
from agents.researcher import run_research
from agents.rewriter import run_rewrite
from agents.auditor import run_audit
from pipeline.digest import generate as generate_digest, send_email
from pipeline.poster import run_posting


# ─── State helpers ────────────────────────────────────────────────────────────

def _state_path(day: str | None = None) -> Path:
    day = day or date.today().isoformat()
    return STATE_DIR / f"posts_{day}.json"


def _load_state(day: str | None = None) -> dict:
    path = _state_path(day)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"date": day or date.today().isoformat(), "pipeline_status": "new", "posts": []}


def _save_state(state: dict, day: str | None = None) -> None:
    path = _state_path(day)
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def _require_status(state: dict, required: str) -> None:
    status = state.get("pipeline_status", "new")
    if status == "new" and required != "researching":
        print(f"❌ Run --research first (current status: {status})")
        sys.exit(1)


# ─── Pipeline stages ──────────────────────────────────────────────────────────

def stage_research() -> None:
    today = date.today().isoformat()
    state = _load_state()
    if state.get("pipeline_status") not in ("new", "researching"):
        print(f"ℹ️  Research already done for {today}. Delete state file to redo.")
        return
    print(f"\n🔍 STAGE 1 — Research  ({today})")
    state["pipeline_status"] = "researching"
    _save_state(state)
    posts = run_research()
    state["posts"] = posts
    state["pipeline_status"] = "researched"
    _save_state(state)
    print(f"\n✅ Research complete — {len(posts)} posts found")
    print(f"   State saved → {_state_path()}")


def stage_rewrite() -> None:
    state = _load_state()
    _require_status(state, "researched")
    if state["pipeline_status"] not in ("researched", "rewriting"):
        print(f"ℹ️  Already rewritten. Status: {state['pipeline_status']}")
        return
    print(f"\n✍️  STAGE 2 — Rewrite  ({state['date']})")
    state["pipeline_status"] = "rewriting"
    _save_state(state)
    state["posts"] = run_rewrite(state["posts"])
    state["pipeline_status"] = "rewritten"
    _save_state(state)
    print(f"\n✅ Rewrite complete")


def stage_audit() -> None:
    state = _load_state()
    if state["pipeline_status"] not in ("rewritten", "auditing"):
        print(f"❌ Run --rewrite first (status: {state['pipeline_status']})")
        sys.exit(1)
    print(f"\n🔬 STAGE 3 — PhD Audit  ({state['date']})")
    state["pipeline_status"] = "auditing"
    _save_state(state)
    state["posts"] = run_audit(state["posts"])
    state["pipeline_status"] = "audited"
    _save_state(state)
    print(f"\n✅ Audit complete")


def stage_digest() -> None:
    state = _load_state()
    if state["pipeline_status"] not in ("audited", "digest_sent"):
        print(f"❌ Run --audit first (status: {state['pipeline_status']})")
        sys.exit(1)
    print(f"\n📄 STAGE 4 — Generate Digest  ({state['date']})")
    digest_path = generate_digest(state["posts"])
    send_email(digest_path)
    state["pipeline_status"] = "digest_sent"
    _save_state(state)
    print(f"\n✅ Digest ready. Open in browser:")
    print(f"   open {digest_path}   (macOS)")
    print(f"   xdg-open {digest_path}   (Linux)")
    print(f"\nThen approve posts with:")
    print(f"   python main.py --approve <post_id> [<post_id> ...]")


def stage_post() -> None:
    state = _load_state()
    if state["pipeline_status"] not in ("digest_sent", "posting", "complete"):
        print(f"❌ Run --digest and approve posts first (status: {state['pipeline_status']})")
        sys.exit(1)
    approved = [p for p in state["posts"] if p["approval"]["status"] == "approved"]
    if not approved:
        print("⚠️  No approved posts found. Approve some with --approve <id>")
        return
    print(f"\n📤 STAGE 5 — Post  ({state['date']})  [{len(approved)} approved]")
    state["pipeline_status"] = "posting"
    _save_state(state)
    state["posts"] = run_posting(state["posts"])
    state["pipeline_status"] = "complete"
    _save_state(state)
    print(f"\n✅ Posting complete")


# ─── Approval helpers ─────────────────────────────────────────────────────────

def approve_posts(ids: list[str]) -> None:
    state = _load_state()
    count = 0
    for post in state["posts"]:
        if post["id"] in ids:
            post["approval"]["status"] = "approved"
            post["approval"]["user_decision"] = "approved"
            post["approval"]["decided_at"] = datetime.now(timezone.utc).isoformat()
            count += 1
            print(f"  ✅ Approved [{post['platform']}] {post['id'][:8]}...")
    _save_state(state)
    print(f"\nApproved {count} post(s)")


def reject_post(post_id: str, note: str) -> None:
    state = _load_state()
    for post in state["posts"]:
        if post["id"] == post_id:
            post["approval"]["status"] = "rejected"
            post["approval"]["user_decision"] = "rejected"
            post["approval"]["user_notes"] = note
            post["approval"]["decided_at"] = datetime.now(timezone.utc).isoformat()
            print(f"  ❌ Rejected [{post['platform']}] {post_id[:8]}... Note: {note or '—'}")
    _save_state(state)


def show_status() -> None:
    state = _load_state()
    print(f"\n📊 Status for {state['date']}  →  pipeline: {state['pipeline_status'].upper()}")
    print(f"{'ID':38} {'Platform':12} {'Audit':8} {'Score':6} {'Approval':12} {'Post':12}")
    print("─" * 100)
    for p in state["posts"]:
        audit = p.get("audit") or {}
        rec   = audit.get("recommendation", "—")
        score = f"{audit.get('overall_score', 0):.1f}"
        app   = p["approval"]["status"]
        post  = p["posting"]["status"]
        print(f"{p['id']:38} {p['platform']:12} {rec:8} {score:6} {app:12} {post:12}")


# ─── Full pipeline ─────────────────────────────────────────────────────────────

def run_once() -> None:
    stage_research()
    stage_rewrite()
    stage_audit()
    stage_digest()
    print("\n⏳ Pipeline complete. Review the digest and run --post after approving.")


def run_schedule() -> None:
    try:
        import schedule
        import time
    except ImportError:
        print("❌ 'schedule' not installed. Run: pip install schedule")
        sys.exit(1)

    def full_pipeline():
        try:
            run_once()
        except Exception as e:
            print(f"❌ Pipeline error: {e}")

    print(f"⏰ Scheduling daily pipeline at {DAILY_RUN_TIME}")
    schedule.every().day.at(DAILY_RUN_TIME).do(full_pipeline)

    # Also schedule posting at 09:00 (assumes user approves after digest at 06:00-ish)
    schedule.every().day.at("09:00").do(stage_post)

    print("Running... (Ctrl+C to stop)\n")
    while True:
        schedule.run_pending()
        time.sleep(30)


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Viral Social Agent — daily research → rewrite → audit → review → post",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--research",  action="store_true", help="Stage 1: find viral posts")
    parser.add_argument("--rewrite",   action="store_true", help="Stage 2: rewrite for each platform")
    parser.add_argument("--audit",     action="store_true", help="Stage 3: PhD expert audit")
    parser.add_argument("--digest",    action="store_true", help="Stage 4: generate HTML digest + email")
    parser.add_argument("--post",      action="store_true", help="Stage 5: post approved content")
    parser.add_argument("--approve",   nargs="+", metavar="POST_ID", help="Approve one or more posts by ID")
    parser.add_argument("--reject",    metavar="POST_ID",            help="Reject a post by ID")
    parser.add_argument("--note",      default="",                   help="Rejection reason (use with --reject)")
    parser.add_argument("--status",    action="store_true",          help="Show today's pipeline status")
    parser.add_argument("--run-once",  action="store_true",          help="Run full pipeline once now")
    parser.add_argument("--schedule",  action="store_true",          help="Run full pipeline on daily schedule")

    args = parser.parse_args()

    if not any(vars(args).values()):
        parser.print_help()
        return

    if not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ ANTHROPIC_API_KEY is not set. Copy .env.example to .env and fill it in.")
        sys.exit(1)

    if args.research:   stage_research()
    if args.rewrite:    stage_rewrite()
    if args.audit:      stage_audit()
    if args.digest:     stage_digest()
    if args.approve:    approve_posts(args.approve)
    if args.reject:     reject_post(args.reject, args.note)
    if args.post:       stage_post()
    if args.status:     show_status()
    if args.run_once:   run_once()
    if args.schedule:   run_schedule()


if __name__ == "__main__":
    main()
