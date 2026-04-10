"""
github.py — GitHub API integration
Reads current radar context and raises PRs.
"""

import logging
import os
import re
from datetime import date

import requests

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"
REPO = "halmstraw/medtech-platform-docs"
RADAR_PATH = "radar/data/radar"
BRANCH_BASE = "main"


def _headers() -> dict:
    token = os.environ["GITHUB_TOKEN"]
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def get_radar_context() -> str:
    """Fetch existing radar entries to give Claude context."""

    # Get the latest release folder
    url = f"{GITHUB_API}/repos/{REPO}/contents/{RADAR_PATH}"
    resp = requests.get(url, headers=_headers(), timeout=10)
    resp.raise_for_status()

    folders = sorted([f["name"] for f in resp.json() if f["type"] == "dir"], reverse=True)
    if not folders:
        return "No existing entries."

    latest_folder = folders[0]
    url = f"{GITHUB_API}/repos/{REPO}/contents/{RADAR_PATH}/{latest_folder}"
    resp = requests.get(url, headers=_headers(), timeout=10)
    resp.raise_for_status()

    entries = []
    for file in resp.json():
        if not file["name"].endswith(".md"):
            continue
        file_resp = requests.get(file["download_url"], timeout=10)
        if file_resp.ok:
            # Extract just the frontmatter for context
            content = file_resp.text
            match = re.match(r"---\n(.*?)\n---", content, re.DOTALL)
            if match:
                entries.append(f"# {file['name']}\n{match.group(1)}")

    return "\n\n".join(entries[:30])  # Cap at 30 entries to stay within token budget


def raise_pr(title: str, filename: str, content: str, suggestion: str) -> str:
    """Create a new branch, commit the radar entry, and open a PR. Returns PR URL."""

    # Create a branch name from the title
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    branch = f"radar/add-{slug}"
    today = date.today().isoformat()

    # Get current main SHA
    ref_url = f"{GITHUB_API}/repos/{REPO}/git/ref/heads/{BRANCH_BASE}"
    resp = requests.get(ref_url, headers=_headers(), timeout=10)
    resp.raise_for_status()
    base_sha = resp.json()["object"]["sha"]

    # Create branch
    requests.post(
        f"{GITHUB_API}/repos/{REPO}/git/refs",
        headers=_headers(),
        json={"ref": f"refs/heads/{branch}", "sha": base_sha},
        timeout=10,
    ).raise_for_status()

    # Get latest release folder
    folders_resp = requests.get(
        f"{GITHUB_API}/repos/{REPO}/contents/{RADAR_PATH}",
        headers=_headers(),
        timeout=10,
    )
    folders_resp.raise_for_status()
    folders = sorted([f["name"] for f in folders_resp.json() if f["type"] == "dir"], reverse=True)
    release_folder = folders[0] if folders else today

    # Commit the file
    import base64
    file_path = f"{RADAR_PATH}/{release_folder}/{filename}"
    encoded = base64.b64encode(content.encode()).decode()

    requests.put(
        f"{GITHUB_API}/repos/{REPO}/contents/{file_path}",
        headers=_headers(),
        json={
            "message": f"feat(radar): add {title} via radar bot",
            "content": encoded,
            "branch": branch,
        },
        timeout=10,
    ).raise_for_status()

    # Open PR
    pr_resp = requests.post(
        f"{GITHUB_API}/repos/{REPO}/pulls",
        headers=_headers(),
        json={
            "title": f"Radar: Add {title}",
            "body": f"## Radar entry: {title}\n\nSuggested via Telegram radar bot.\n\n**Original suggestion:** {suggestion}\n\n**File:** `{file_path}`",
            "head": branch,
            "base": BRANCH_BASE,
        },
        timeout=10,
    )
    pr_resp.raise_for_status()
    return pr_resp.json()["html_url"]
