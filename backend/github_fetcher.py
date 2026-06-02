"""Fetch GitHub repo metadata and README for summarization."""

import base64
import json
import re
from urllib.request import Request, urlopen

GITHUB_API = "https://api.github.com"
USER_AGENT = "REACH-App/1.0"
REQUEST_TIMEOUT = 10

_REPO_URL_RE = re.compile(r"github\.com/([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+)")


def validate_repo_url(url: str) -> tuple[str, str]:
    """Extract owner and repo name from a GitHub URL. Raises ValueError if invalid."""
    match = _REPO_URL_RE.search(url.rstrip("/"))
    if not match:
        raise ValueError("Invalid GitHub repo URL. Use format: https://github.com/owner/repo")
    return match.group(1), match.group(2)


def _github_get(path: str) -> dict | list | None:
    """Hit the GitHub API. Returns parsed JSON or None on 404."""
    try:
        req = Request(
            f"{GITHUB_API}{path}",
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/vnd.github.v3+json",
            },
        )
        resp = urlopen(req, timeout=REQUEST_TIMEOUT)
        return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def fetch_repo_metadata(owner: str, repo: str) -> dict:
    """Fetch repo info and README from GitHub API.

    Returns dict with keys: repo_name, description, language, stars, readme, warning.
    Raises ValueError if repo fails quality checks.
    """
    repo_data = _github_get(f"/repos/{owner}/{repo}")
    if not repo_data:
        raise ValueError("Could not fetch repo from GitHub. Check the URL and make sure it's a public repo.")

    if repo_data.get("fork") and repo_data.get("stargazers_count", 0) == 0:
        raise ValueError("This looks like an unmodified fork.")

    readme_data = _github_get(f"/repos/{owner}/{repo}/readme")
    readme_text = ""
    if readme_data and readme_data.get("content"):
        try:
            readme_text = base64.b64decode(readme_data["content"]).decode("utf-8", errors="ignore")
        except Exception:
            readme_text = ""

    if len(readme_text.strip()) < 50:
        raise ValueError(
            "This repo doesn't have a README. Add one so founders know what it does."
        )

    warning = None
    if not repo_data.get("description"):
        warning = "This repo has no description. Consider adding one on GitHub."

    return {
        "repo_name": repo_data.get("name", repo),
        "description": repo_data.get("description"),
        "language": repo_data.get("language"),
        "stars": repo_data.get("stargazers_count", 0),
        "readme": readme_text[:2000],
        "warning": warning,
    }
