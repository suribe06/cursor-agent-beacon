#!/usr/bin/env python3
"""Simulate a Cursor hook invocation for local testing."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Simulate a Cursor hook call")
    parser.add_argument(
        "event_file",
        type=Path,
        help="Path to a sample hook JSON payload",
    )
    parser.add_argument(
        "--handler",
        type=Path,
        default=Path(".cursor/hooks/hook-handler.py"),
        help="Hook handler script path",
    )
    args = parser.parse_args()

    payload = args.event_file.read_text(encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(args.handler)],
        input=payload,
        text=True,
        capture_output=True,
        check=False,
    )

    if result.stderr:
        print(result.stderr, file=sys.stderr, end="")

    stdout = result.stdout.strip()
    if stdout:
        try:
            parsed = json.loads(stdout)
            print(json.dumps(parsed, indent=2))
        except json.JSONDecodeError:
            print(stdout)

    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
