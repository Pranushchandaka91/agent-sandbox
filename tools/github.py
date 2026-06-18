import base64
import requests

_BASE = "https://api.github.com"
_HEADERS = {"Accept": "application/vnd.github+json", "User-Agent": "agent-sandbox"}


def _validate_repo(repo: str):
    if not repo or not repo.strip() or "/" not in repo:
        return {"status": "error", "data": None, "error": "repo must be in 'owner/name' format."}
    return None


def _handle_error(r, repo: str):
    if r.status_code == 404:
        return {"status": "error", "data": None, "error": f"Repository '{repo}' not found."}
    if r.status_code == 403:
        return {"status": "error", "data": None, "error": "GitHub API rate limit reached. Try again later."}
    if not r.ok:
        return {"status": "error", "data": None, "error": f"GitHub API error: {r.status_code}"}
    return None


def github_repo_info(repo: str) -> dict:
    err = _validate_repo(repo)
    if err:
        return err
    try:
        r = requests.get(f"{_BASE}/repos/{repo}", headers=_HEADERS, timeout=10)
    except Exception as e:
        return {"status": "error", "data": None, "error": str(e)}
    err = _handle_error(r, repo)
    if err:
        return err
    body = r.json()
    return {
        "status": "success",
        "data": {
            "full_name":    body.get("full_name"),
            "description":  body.get("description"),
            "stars":        body.get("stargazers_count"),
            "language":     body.get("language"),
            "open_issues":  body.get("open_issues_count"),
            "url":          body.get("html_url"),
            "last_updated": body.get("updated_at"),
        },
        "error": None,
    }


def github_readme(repo: str) -> dict:
    err = _validate_repo(repo)
    if err:
        return err
    try:
        r = requests.get(f"{_BASE}/repos/{repo}/readme", headers=_HEADERS, timeout=10)
    except Exception as e:
        return {"status": "error", "data": None, "error": str(e)}
    err = _handle_error(r, repo)
    if err:
        return err
    body = r.json()
    readme_text = base64.b64decode(body.get("content", "")).decode("utf-8", errors="replace")
    return {
        "status": "success",
        "data": {
            "repo":        repo,
            "readme_text": readme_text,
            "length":      len(readme_text),
        },
        "error": None,
    }
