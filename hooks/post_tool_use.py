#!/usr/bin/env python
"""
PostToolUse hook — runs after every Claude Code tool call.
Responsibilities:
  1. Log tool output and execution result
  2. Flag unexpected outputs for review
"""

import json
import sys
import os
from datetime import datetime

LOG_DIR = os.path.join(os.path.dirname(__file__), "..", ".claude", "logs")

SENSITIVE_PATTERNS = [
    "password",
    "secret",
    "token",
    "api_key",
    "private_key",
]


def ensure_log_dir():
    os.makedirs(LOG_DIR, exist_ok=True)


def contains_sensitive_data(output: str) -> bool:
    output_lower = output.lower()
    return any(pattern in output_lower for pattern in SENSITIVE_PATTERNS)


def log_tool_result(tool_name: str, output: str, flagged: bool):
    ensure_log_dir()
    log_file = os.path.join(LOG_DIR, f"audit_{datetime.now().strftime('%Y-%m-%d')}.jsonl")
    entry = {
        "timestamp": datetime.now().isoformat(),
        "event": "PostToolUse",
        "tool": tool_name,
        "output_preview": output[:500] if output else "",
        "output_length": len(output) if output else 0,
        "flagged_sensitive": flagged,
    }
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def main():
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw)
    except Exception as e:
        print(json.dumps({"action": "allow", "error": str(e)}))
        return

    tool_name = payload.get("tool_name", "")
    tool_output = payload.get("tool_response", {})

    # Extract text output
    output_text = ""
    if isinstance(tool_output, str):
        output_text = tool_output
    elif isinstance(tool_output, dict):
        output_text = tool_output.get("output", "") or json.dumps(tool_output)

    flagged = contains_sensitive_data(output_text)
    log_tool_result(tool_name, output_text, flagged=flagged)

    if flagged:
        print(json.dumps({
            "action": "warn",
            "message": "[PostToolUse Hook] Possible sensitive data detected in tool output. Review audit log.",
        }))
    else:
        print(json.dumps({"action": "allow"}))


if __name__ == "__main__":
    main()