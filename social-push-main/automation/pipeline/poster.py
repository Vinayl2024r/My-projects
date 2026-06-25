"""
Poster agent: posts approved content to each platform using agent-browser.
Runs Claude in an agentic loop that calls agent-browser commands via subprocess.
Platforms without auto-post support (YouTube, WhatsApp) are logged as skipped.
"""
import subprocess
import textwrap
from datetime import datetime, timezone
from pathlib import Path

import anthropic

from config import ANTHROPIC_API_KEY, MODEL, PLATFORM_SPECS, SKILLS_DIR

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# Load agent-browser skill reference as context for the posting agent
_AB_SKILL = (Path(__file__).parent.parent.parent / "skills" / "agent-browser" / "SKILL.md")
AGENT_BROWSER_DOCS = _AB_SKILL.read_text(encoding="utf-8") if _AB_SKILL.exists() else ""

POSTER_SYSTEM = """You are a social media posting agent that controls a browser via agent-browser CLI.

agent-browser reference:
{ab_docs}

Platform workflow:
{workflow}

CRITICAL RULES:
1. Use --auto-connect for all agent-browser commands.
2. Always run `agent-browser --auto-connect snapshot -i` BEFORE clicking/filling to get fresh refs.
3. Re-snapshot after every navigation or dynamic content change.
4. Fill in the post content exactly as given — do NOT modify it.
5. STOP before clicking the final Publish/Post/Share button. Leave the draft ready.
6. When done, call the bash tool with just the word DONE to signal completion.

If a step fails, try agent-browser find or agent-browser eval to locate the element."""


def _load_workflow(platform: str) -> str:
    spec = PLATFORM_SPECS.get(platform, {})
    ref = spec.get("workflow_ref")
    if ref and Path(ref).exists():
        return Path(ref).read_text(encoding="utf-8")
    return f"No pre-written workflow for {platform}. Discover the UI using snapshot and interact step-by-step."


def _run_bash(command: str) -> str:
    """Execute an agent-browser shell command and return stdout+stderr."""
    if command.strip() == "DONE":
        return "DONE"
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=60
        )
        return (result.stdout + result.stderr).strip() or "(no output)"
    except subprocess.TimeoutExpired:
        return "ERROR: command timed out after 60s"
    except Exception as e:
        return f"ERROR: {e}"


def post_to_platform(post: dict) -> dict:
    platform = post["platform"]
    spec = PLATFORM_SPECS[platform]

    if not spec.get("supports_auto_post"):
        post["posting"]["status"] = "skipped"
        post["posting"]["error"] = spec.get("skip_reason", "Auto-post not supported")
        print(f"  ⏭  [{platform}] Skipped — {post['posting']['error']}")
        return post

    content = post["rewritten_text"]
    if post["hashtags"]:
        content += "\n\n" + " ".join(post["hashtags"])

    workflow = _load_workflow(platform)
    system = POSTER_SYSTEM.format(ab_docs=AGENT_BROWSER_DOCS[:3000], workflow=workflow)

    session = spec.get("session_name") or platform
    messages: list[dict] = [{
        "role": "user",
        "content": textwrap.dedent(f"""
            Post the following content to {platform}.
            Use session name: {session}

            === POST CONTENT ===
            {content}
            ====================

            Follow the platform workflow. Stop before the final publish button.
        """).strip(),
    }]

    bash_tool = {"name": "bash", "description": "Run a shell command", "input_schema": {
        "type": "object",
        "properties": {"command": {"type": "string"}},
        "required": ["command"],
    }}

    print(f"  🤖 [{platform}] Starting posting agent...")
    for _ in range(20):  # max 20 tool-call rounds per post
        response = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=system,
            tools=[bash_tool],
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            post["posting"]["status"] = "draft_ready"
            post["posting"]["posted_at"] = datetime.now(timezone.utc).isoformat()
            print(f"  ✅ [{platform}] Draft ready — awaiting manual publish")
            break

        messages.append({"role": "assistant", "content": response.content})
        tool_results = []
        done = False

        for block in response.content:
            if block.type == "tool_use" and block.name == "bash":
                cmd = block.input.get("command", "")
                print(f"     $ {cmd[:80]}")
                output = _run_bash(cmd)
                if output == "DONE":
                    done = True
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": output if output != "DONE" else "Posting complete.",
                })

        messages.append({"role": "user", "content": tool_results})

        if done:
            post["posting"]["status"] = "draft_ready"
            post["posting"]["posted_at"] = datetime.now(timezone.utc).isoformat()
            print(f"  ✅ [{platform}] Draft ready — awaiting manual publish")
            break
    else:
        post["posting"]["status"] = "error"
        post["posting"]["error"] = "Agent exceeded max rounds without completing"
        print(f"  ❌ [{platform}] Posting agent timed out")

    return post


def run_posting(posts: list[dict]) -> list[dict]:
    approved = [p for p in posts if p["approval"]["status"] == "approved"]
    print(f"  📤 Posting {len(approved)} approved post(s)...")
    for i, post in enumerate(posts):
        if post["approval"]["status"] != "approved":
            continue
        try:
            posts[i] = post_to_platform(post)
        except Exception as e:
            posts[i]["posting"]["status"] = "error"
            posts[i]["posting"]["error"] = str(e)
            print(f"  ❌ [{post['platform']}] Error: {e}")
    return posts
