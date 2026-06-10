#!/usr/bin/env python
"""
PreToolUse hook — runs before every Claude Code tool call.
Responsibilities:
  1. Log every tool call attempt with timestamp
  2. Block dangerous commands (write operations on target repo)
"""

import json
import sys
import os
from datetime import datetime

# --- Configuration ---
LOG_DIR = os.path.join(os.path.dirname(__file__), "..", ".claude", "logs")
BLOCKED_PATTERNS = [
    "git push",
    "git commit",
    "git merge",
    "git rebase",
    "git reset --hard",
    "rm -rf",
    "rm -f",
    "mv ",
    "chmod",
    "sudo",
]
TARGET_REPO_PATH = "/d/IA/workspace/inventory-management"


def ensure_log_dir():
    os.makedirs(LOG_DIR, exist_ok=True)


def log_tool_call(tool_name: str, tool_input: dict, blocked: bool, reason: str = ""):
    ensure_log_dir()
    log_file = os.path.join(LOG_DIR, f"audit_{datetime.now().strftime('%Y-%m-%d')}.jsonl")
    entry = {
        "timestamp": datetime.now().isoformat(),
        "event": "PreToolUse",
        "tool": tool_name,
        "input": tool_input,
        "blocked": blocked,
        "reason": reason,
    }
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def is_dangerous(tool_name: str, tool_input: dict) -> tuple[bool, str]:
    """Returns (is_dangerous, reason)."""
    if tool_name != "Bash":
        return False, ""

    command = tool_input.get("command", "")

    for pattern in BLOCKED_PATTERNS:
        if pattern in command:
            return True, f"Blocked pattern detected: '{pattern}'"

    # Block any write operation targeting the inventory-management repo
    if TARGET_REPO_PATH in command and any(
        op in command for op in ["echo ", ">", "tee ", "touch ", "mkdir "]
    ):
        return True, f"Write operation attempted on protected path: {TARGET_REPO_PATH}"

    return False, ""


def main():
    # Claude Code passes tool info via stdin as JSON
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw)
    except Exception as e:
        # If we can't parse input, allow the tool call but log the error
        print(json.dumps({"action": "allow", "error": str(e)}))
        return

    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input", {})

    dangerous, reason = is_dangerous(tool_name, tool_input)
    log_tool_call(tool_name, tool_input, blocked=dangerous, reason=reason)

    if dangerous:
        # Returning "block" with a message stops the tool call
        response = {
            "action": "block",
            "message": f"[PreToolUse Hook] Blocked: {reason}",
        }
    else:
        response = {"action": "allow"}

    print(json.dumps(response))


if __name__ == "__main__":
    main()