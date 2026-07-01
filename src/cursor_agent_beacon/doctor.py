"""Health checks and status display for end-user troubleshooting."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from io import StringIO
from pathlib import Path

from cursor_agent_beacon.hooks import SUPPORTED_HOOKS
from cursor_agent_beacon.install import (
    BEACON_HOOK_MARKER,
    DEFAULT_STATUS_FILE,
    DEFAULT_WRAPPER_PATH,
)
from cursor_agent_beacon.setup import gnome_extension_available, resolve_beacon_bin

_PROBE_EVENT = {
    "hook_event_name": "sessionStart",
    "conversation_id": "doctor-probe",
    "generation_id": "doctor-probe",
}


@dataclass(frozen=True, slots=True)
class CheckResult:
    name: str
    ok: bool
    detail: str
    hint: str | None = None


def _parse_wrapper_bin(wrapper_text: str) -> Path | None:
    match = re.search(r'exec\s+"([^"]+)"\s+run', wrapper_text)
    if match:
        return Path(match.group(1))
    match = re.search(r"exec\s+(\S+)\s+run", wrapper_text)
    if match:
        return Path(match.group(1))
    return None


def _beacon_hooks_in_config(hooks_path: Path) -> tuple[int, int]:
    try:
        payload = json.loads(hooks_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 0, len(SUPPORTED_HOOKS)
    hooks = payload.get("hooks") or {}
    found = 0
    for hook_name in SUPPORTED_HOOKS:
        entries = hooks.get(hook_name) or []
        if any(BEACON_HOOK_MARKER in str(item.get("command", "")) for item in entries):
            found += 1
    return found, len(SUPPORTED_HOOKS)


def _gnome_extension_enabled() -> bool | None:
    if not shutil.which("gnome-extensions"):
        return None
    from cursor_agent_beacon.install import GNOME_UUID

    result = subprocess.run(
        ["gnome-extensions", "list", "--enabled"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return GNOME_UUID in result.stdout


def run_doctor(
    *,
    cursor_dir: Path | None = None,
    status_file: Path | None = None,
    wrapper_path: Path | None = None,
    probe: bool = False,
) -> list[CheckResult]:
    """Run install health checks. Returns list of results (ok=False = failure)."""
    cursor_dir = cursor_dir or Path.home() / ".cursor"
    status_file = status_file or DEFAULT_STATUS_FILE
    wrapper_path = wrapper_path or DEFAULT_WRAPPER_PATH
    hooks_path = cursor_dir / "hooks.json"
    results: list[CheckResult] = []

    try:
        import cursor_agent_beacon  # noqa: F401

        bin_path = resolve_beacon_bin(None)
        results.append(
            CheckResult(
                "package",
                True,
                f"import ok ({bin_path})",
            )
        )
    except (RuntimeError, FileNotFoundError) as exc:
        results.append(
            CheckResult(
                "package",
                False,
                str(exc),
                hint="Run ./setup.sh from the repository root",
            )
        )
        bin_path = None

    if wrapper_path.is_file():
        wrapper_text = wrapper_path.read_text(encoding="utf-8")
        if os.access(wrapper_path, os.X_OK):
            results.append(CheckResult("hook wrapper", True, str(wrapper_path)))
        else:
            results.append(
                CheckResult(
                    "hook wrapper",
                    False,
                    f"not executable: {wrapper_path}",
                    hint="Run ./setup.sh",
                )
            )
        wrapped_bin = _parse_wrapper_bin(wrapper_text)
        if wrapped_bin is None:
            results.append(
                CheckResult(
                    "wrapper target",
                    False,
                    "could not parse exec line in wrapper",
                    hint="Re-run ./setup.sh",
                )
            )
        elif wrapped_bin.is_file():
            results.append(
                CheckResult("wrapper target", True, str(wrapped_bin.resolve()))
            )
        else:
            results.append(
                CheckResult(
                    "wrapper target",
                    False,
                    f"missing binary: {wrapped_bin}",
                    hint="Re-run ./setup.sh (repo moved or .venv deleted?)",
                )
            )
    else:
        results.append(
            CheckResult(
                "hook wrapper",
                False,
                f"not found: {wrapper_path}",
                hint="Run ./setup.sh",
            )
        )

    if hooks_path.is_file():
        found, total = _beacon_hooks_in_config(hooks_path)
        ok = found == total
        results.append(
            CheckResult(
                "hooks.json",
                ok,
                f"{found}/{total} beacon hooks in {hooks_path}",
                None if ok else "Run ./setup.sh",
            )
        )
    else:
        results.append(
            CheckResult(
                "hooks.json",
                False,
                f"not found: {hooks_path}",
                hint="Run ./setup.sh",
            )
        )

    try:
        status_file.parent.mkdir(parents=True, exist_ok=True)
        probe_path = status_file.parent / ".doctor-write-test"
        probe_path.write_text("ok", encoding="utf-8")
        probe_path.unlink(missing_ok=True)
        results.append(
            CheckResult("status dir", True, f"writable {status_file.parent}")
        )
    except OSError as exc:
        results.append(
            CheckResult(
                "status dir",
                False,
                f"{status_file.parent}: {exc}",
            )
        )

    if gnome_extension_available():
        from cursor_agent_beacon.install import GNOME_UUID

        ext_dir = Path.home() / ".local/share/gnome-shell/extensions" / GNOME_UUID
        if ext_dir.is_dir():
            enabled = _gnome_extension_enabled()
            if enabled is True:
                results.append(
                    CheckResult("GNOME panel", True, f"enabled ({ext_dir.name})")
                )
            elif enabled is False:
                results.append(
                    CheckResult(
                        "GNOME panel",
                        False,
                        "installed but not enabled",
                        hint=f"Run: gnome-extensions enable {GNOME_UUID}",
                    )
                )
            else:
                results.append(
                    CheckResult(
                        "GNOME panel",
                        True,
                        f"installed ({ext_dir})",
                    )
                )
        else:
            results.append(
                CheckResult(
                    "GNOME panel",
                    True,
                    "not installed (optional — run ./setup.sh without --hooks-only)",
                )
            )

    results.append(
        CheckResult(
            "cursor restart",
            True,
            "restart Cursor after changing hooks (loads at startup)",
        )
    )

    if probe and bin_path is not None:
        results.append(_probe_hook_handler(status_file, bin_path))

    return results


def _probe_hook_handler(status_file: Path, beacon_bin: Path) -> CheckResult:
    from cursor_agent_beacon.handler import run_hook_handler
    from cursor_agent_beacon.sinks.file import FileStatusSink

    sink = FileStatusSink(status_file)
    env = os.environ.copy()
    env["CURSOR_AGENT_BEACON_STATUS_FILE"] = str(status_file)
    try:
        code = run_hook_handler(
            stdin=StringIO(json.dumps(_PROBE_EVENT)),
            stdout=StringIO(),
            stderr=StringIO(),
            sink=sink,
        )
    except Exception as exc:  # noqa: BLE001
        return CheckResult("hook probe", False, str(exc))

    if code != 0:
        return CheckResult("hook probe", False, f"handler exit {code}")

    if not status_file.is_file():
        return CheckResult(
            "hook probe",
            False,
            f"handler ran but {status_file} missing",
        )

    try:
        payload = json.loads(status_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return CheckResult("hook probe", False, str(exc))

    if payload.get("state") != "idle":
        return CheckResult(
            "hook probe",
            False,
            f"unexpected state: {payload.get('state')}",
        )

    return CheckResult(
        "hook probe",
        True,
        f"wrote {status_file} via {beacon_bin.name}",
    )


def format_doctor_report(results: list[CheckResult]) -> str:
    lines: list[str] = []
    failures = 0
    for item in results:
        mark = "✓" if item.ok else "✗"
        if not item.ok and item.name != "cursor restart":
            failures += 1
        lines.append(f"{mark} {item.name}: {item.detail}")
        if item.hint and not item.ok:
            lines.append(f"    → {item.hint}")
    lines.append("")
    if failures:
        lines.append(f"{failures} check(s) failed.")
    else:
        lines.append("All checks passed.")
        lines.append("Run an Agent chat, then: cursor-agent-beacon status")
    return "\n".join(lines)


def doctor_exit_code(results: list[CheckResult]) -> int:
    for item in results:
        if not item.ok and item.name not in {"cursor restart"}:
            return 1
    return 0


def read_status_payload(status_file: Path | None = None) -> dict:
    path = status_file or DEFAULT_STATUS_FILE
    if not path.is_file():
        raise FileNotFoundError(f"No status file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def format_status_report(payload: dict, *, status_file: Path | None = None) -> str:
    path = status_file or DEFAULT_STATUS_FILE
    state = payload.get("state", "unknown")
    message = payload.get("message", "—")
    project = payload.get("project") or payload.get("label") or "—"
    hook = payload.get("hook_event_name", "—")
    ts = payload.get("updated_at") or payload.get("timestamp") or "—"
    focus = payload.get("focused_conversation_id")
    active = payload.get("active_count")

    lines = [
        f"State:    {state}",
        f"Message:  {message}",
        f"Project:  {project}",
        f"Hook:     {hook}",
        f"Updated:  {ts}",
    ]
    if focus:
        lines.append(f"Focus:    {focus}")
    if active is not None:
        lines.append(f"Active:   {active}")
    if payload.get("started_at"):
        lines.append(f"Turn:     since {payload['started_at']}")
    lines.append(f"File:     {path}")
    registry = path.parent / "registry.json"
    if registry.is_file():
        lines.append(f"Registry: {registry}")
    return "\n".join(lines)
