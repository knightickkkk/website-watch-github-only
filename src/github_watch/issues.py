from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen
import json
import os
import re


@dataclass(slots=True)
class WatchRequest:
    issue_number: int
    issue_url: str
    issue_title: str
    email: str
    website: str
    selector: str
    compare_mode: str

    @property
    def key(self) -> str:
        return f"issue-{self.issue_number}"


def load_watch_requests() -> list[WatchRequest]:
    repository = os.environ.get("GITHUB_REPOSITORY")
    token = os.environ.get("GITHUB_TOKEN")
    if not repository or not token:
        raise RuntimeError("GITHUB_REPOSITORY and GITHUB_TOKEN are required.")

    issues = _fetch_issues(repository, token)
    requests: list[WatchRequest] = []

    for issue in issues:
        if "pull_request" in issue:
            continue
        try:
            requests.append(_parse_issue(issue))
        except ValueError as exc:
            print(f"Skipping issue #{issue.get('number')}: {exc}")

    return requests


def _fetch_issues(repository: str, token: str) -> list[dict[str, Any]]:
    url = (
        f"https://api.github.com/repos/{repository}/issues"
        "?state=open&labels=watch-request&per_page=100"
    )
    request = Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "website-watch-github-only",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urlopen(request, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))
    if not isinstance(data, list):
        raise RuntimeError("GitHub API returned an unexpected response.")
    return data


def _parse_issue(issue: dict[str, Any]) -> WatchRequest:
    body = str(issue.get("body") or "")
    email = _field(body, "Email")
    website = _normalize_url(_field(body, "Website"))
    selector = _field(body, "Selector", required=False)
    compare_mode = _field(body, "Compare mode", required=False) or "text"

    if compare_mode not in {"text", "screenshot", "text_or_screenshot"}:
        compare_mode = "text"

    return WatchRequest(
        issue_number=int(issue["number"]),
        issue_url=str(issue.get("html_url") or ""),
        issue_title=str(issue.get("title") or f"Watch request #{issue['number']}"),
        email=email,
        website=website,
        selector=selector,
        compare_mode=compare_mode,
    )


def _field(body: str, name: str, required: bool = True) -> str:
    match = re.search(rf"^{re.escape(name)}:\s*(.*)$", body, flags=re.MULTILINE)
    if not match:
        if required:
            raise ValueError(f"missing field: {name}")
        return ""
    value = match.group(1).strip()
    if required and not value:
        raise ValueError(f"empty field: {name}")
    return value


def _normalize_url(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"invalid website URL: {url}")
    return url
