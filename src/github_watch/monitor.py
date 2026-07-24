from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import asyncio
import difflib

from .browser import Capture, capture_request
from .emailer import EmailConfig, send_email
from .issues import WatchRequest, load_watch_requests
from .state import load_state, save_state


def run_monitor(state_path: Path, screenshot_dir: Path) -> int:
    return asyncio.run(_run_monitor(state_path, screenshot_dir))


async def _run_monitor(state_path: Path, screenshot_dir: Path) -> int:
    requests = load_watch_requests()
    state = load_state(state_path)
    state.setdefault("requests", {})

    checked = 0
    changed = 0
    emailed = 0
    errors = 0
    email_config: EmailConfig | None = None

    for request in requests:
        checked += 1
        try:
            capture = await capture_request(request, screenshot_dir)
        except Exception as exc:
            errors += 1
            print(f"Fetch failed for issue #{request.issue_number}: {exc}")
            continue

        previous = state["requests"].get(request.key)
        did_change = _did_change(request, previous, capture)
        is_baseline = previous is None

        if did_change and not is_baseline:
            changed += 1
            if email_config is None:
                email_config = EmailConfig.from_env()
            try:
                send_email(
                    email_config,
                    to=request.email,
                    subject=f"[Website Watch] Changed: {request.website}",
                    body=_email_body(request, previous, capture),
                    attachments=[capture.screenshot_path],
                )
                emailed += 1
            except Exception as exc:
                errors += 1
                print(f"Email failed for issue #{request.issue_number}: {exc}")

        state["requests"][request.key] = {
            "issue_number": request.issue_number,
            "issue_url": request.issue_url,
            "email": request.email,
            "website": request.website,
            "selector": request.selector,
            "compare_mode": request.compare_mode,
            "title": capture.title,
            "final_url": capture.final_url,
            "text_hash": capture.text_hash,
            "screenshot_hash": capture.screenshot_hash,
            "tracked_text": capture.tracked_text,
            "last_checked_at": datetime.now(ZoneInfo("UTC")).isoformat(),
        }

    save_state(state_path, state)
    print(f"Checked {checked}; changed {changed}; emailed {emailed}; errors {errors}.")
    return 0 if errors == 0 else 1


def _did_change(request: WatchRequest, previous: dict | None, capture: Capture) -> bool:
    if previous is None:
        return True

    if request.compare_mode == "screenshot":
        return previous.get("screenshot_hash") != capture.screenshot_hash

    if request.compare_mode == "text_or_screenshot":
        return (
            previous.get("text_hash") != capture.text_hash
            or previous.get("screenshot_hash") != capture.screenshot_hash
        )

    return previous.get("text_hash") != capture.text_hash


def _email_body(request: WatchRequest, previous: dict | None, capture: Capture) -> str:
    local_time = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S %Z")
    lines = [
        "A watched website changed.",
        "",
        f"Website: {request.website}",
        f"Final URL: {capture.final_url}",
        f"GitHub request: {request.issue_url}",
        f"Checked at: {local_time}",
        "",
        "A screenshot is attached.",
        "",
        "Current tracked text preview:",
        _preview(capture.tracked_text),
    ]

    if previous and previous.get("tracked_text"):
        lines.extend(["", "Text diff:", _diff(previous.get("tracked_text", ""), capture.tracked_text)])

    return "\n".join(lines)


def _preview(text: str, limit: int = 1200) -> str:
    if len(text) <= limit:
        return text or "<empty>"
    return text[:limit].rstrip() + "\n...preview truncated..."


def _diff(old: str, new: str, max_lines: int = 80) -> str:
    old_lines = _chunk(old)
    new_lines = _chunk(new)
    diff_lines = list(
        difflib.unified_diff(old_lines, new_lines, fromfile="previous", tofile="current", lineterm="")
    )
    if len(diff_lines) > max_lines:
        diff_lines = diff_lines[:max_lines] + ["...diff truncated..."]
    return "\n".join(diff_lines) if diff_lines else "<no text diff available>"


def _chunk(text: str, size: int = 120) -> list[str]:
    return [text[index : index + size] for index in range(0, len(text), size)] or [""]
