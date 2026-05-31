"""
History repository integration – Phase 5.

Pushes assessment reports and the SQLite history database to a private
GitHub or Forgejo repository.

Design constraints
------------------
- Authentication is NEVER managed by this module.
  The caller supplies a token string; how that token was obtained
  (SSH agent, KeePassXC, environment variable, token file) is entirely
  the caller's responsibility.
- No credentials are written to disk by this module.
- The module never reads ~/.ssh or any credential store.

Supported remotes
-----------------
GitHub  – https://api.github.com
Forgejo – any base URL, e.g. https://git.example.com

Both implement the same Contents API (Forgejo is GitHub-API-compatible).

Public API
----------
    detect_remote(repo_url) -> RemoteKind  ("github" | "forgejo" | "unknown")
    load_token(token_file)  -> str          (reads token from a plain-text file)
    push_files(repo_url, token, files, message, branch) -> PushResult
    PushResult.ok          bool
    PushResult.pushed      list[str]        paths that were created/updated
    PushResult.errors      list[str]        paths that failed
"""

from __future__ import annotations

import base64
import hashlib
import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

RemoteKind = Literal["github", "forgejo", "unknown"]


# ---------------------------------------------------------------------------
# Remote detection
# ---------------------------------------------------------------------------

def detect_remote(repo_url: str) -> RemoteKind:
    """
    Classify a repository URL as 'github', 'forgejo', or 'unknown'.

    Only HTTPS URLs are classified; SSH remotes cannot use the HTTP API.
      - https://github.com/…       → github
      - https://<any-other-host>/… → forgejo  (Forgejo is GitHub-API-compatible)
      - anything else              → unknown
    """
    url = repo_url.lower()
    # Require HTTPS/HTTP — SSH remotes can't use the Contents API
    if not (url.startswith("https://") or url.startswith("http://")):
        return "unknown"
    if "github.com" in url:
        return "github"
    return "forgejo"


# ---------------------------------------------------------------------------
# Token loading
# ---------------------------------------------------------------------------

def load_token(token_file: str | Path) -> str:
    """
    Read a plain-text token from a file.

    The file must contain exactly one line: the token value.
    Leading/trailing whitespace is stripped.

    Raises FileNotFoundError if the file does not exist.
    Raises ValueError if the file is empty after stripping.
    """
    path = Path(token_file)
    token = path.read_text().strip()
    if not token:
        raise ValueError(f"Token file is empty: {token_file}")
    return token


# ---------------------------------------------------------------------------
# Push result
# ---------------------------------------------------------------------------

@dataclass
class PushResult:
    ok: bool
    pushed: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)

    def summary(self) -> str:
        lines = []
        if self.pushed:
            lines.append(f"Pushed {len(self.pushed)} file(s): {', '.join(self.pushed)}")
        if self.errors:
            lines.append(f"Failed {len(self.errors)} file(s): {', '.join(self.errors)}")
        if not lines:
            lines.append("Nothing pushed.")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Push files
# ---------------------------------------------------------------------------

def push_files(
    repo_url: str,
    token: str,
    files: list[str | Path],
    message: str = "Assessment update",
    branch: str = "main",
    dest_prefix: str = "",
) -> PushResult:
    """
    Push one or more local files to a GitHub/Forgejo repository.

    Parameters
    ----------
    repo_url    : Full repository URL, e.g.
                  https://github.com/owner/repo
                  https://git.example.com/owner/repo
    token       : API token with repo write access.  Caller's responsibility.
    files       : Local file paths to upload.
    message     : Commit message.
    branch      : Target branch (default: main).
    dest_prefix : Optional path prefix inside the repo (e.g. "assessments/").

    Returns a PushResult.  Individual file failures do not abort the batch.
    """
    api_base = _api_base(repo_url)
    owner, repo_name = _owner_repo(repo_url)

    result = PushResult(ok=True)

    for file_path in files:
        path = Path(file_path)
        if not path.exists():
            result.errors.append(str(path))
            result.messages.append(f"File not found: {path}")
            result.ok = False
            continue

        dest_path = (dest_prefix + path.name) if dest_prefix else path.name

        try:
            _put_file(
                api_base=api_base,
                owner=owner,
                repo=repo_name,
                dest_path=dest_path,
                content=path.read_bytes(),
                message=message,
                branch=branch,
                token=token,
            )
            result.pushed.append(dest_path)
            result.messages.append(f"OK: {dest_path}")
        except Exception as exc:
            result.errors.append(dest_path)
            result.messages.append(f"ERROR {dest_path}: {exc}")
            result.ok = False

    return result


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _api_base(repo_url: str) -> str:
    """Derive the API base URL from a repository URL."""
    url = repo_url.rstrip("/")
    if "github.com" in url:
        return "https://api.github.com"
    # For Forgejo / self-hosted: the API is at <instance>/api/v1
    parsed = urllib.parse.urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}/api/v1"


def _owner_repo(repo_url: str) -> tuple[str, str]:
    """Extract (owner, repo) from a repository URL."""
    url = repo_url.rstrip("/")
    # Strip .git suffix
    if url.endswith(".git"):
        url = url[:-4]
    parts = url.rstrip("/").split("/")
    if len(parts) < 2:
        raise ValueError(f"Cannot parse owner/repo from URL: {repo_url}")
    return parts[-2], parts[-1]


def _put_file(
    api_base: str,
    owner: str,
    repo: str,
    dest_path: str,
    content: bytes,
    message: str,
    branch: str,
    token: str,
) -> None:
    """
    Create or update a single file via the GitHub/Forgejo Contents API.

    PUT /repos/{owner}/{repo}/contents/{path}
    """
    # GitHub API uses /repos/…; Forgejo uses /api/v1/repos/…
    if "api.github.com" in api_base:
        url = f"{api_base}/repos/{owner}/{repo}/contents/{dest_path}"
    else:
        url = f"{api_base}/repos/{owner}/{repo}/contents/{dest_path}"

    encoded = base64.b64encode(content).decode()

    # Check if the file already exists so we can supply the required SHA
    existing_sha = _get_file_sha(api_base, owner, repo, dest_path, branch, token)

    body: dict = {
        "message": message,
        "content": encoded,
        "branch": branch,
    }
    if existing_sha:
        body["sha"] = existing_sha

    _api_request("PUT", url, token, body)


def _get_file_sha(
    api_base: str,
    owner: str,
    repo: str,
    path: str,
    branch: str,
    token: str,
) -> str | None:
    """Return the current blob SHA of a file, or None if it doesn't exist."""
    if "api.github.com" in api_base:
        url = f"{api_base}/repos/{owner}/{repo}/contents/{path}?ref={branch}"
    else:
        url = f"{api_base}/repos/{owner}/{repo}/contents/{path}?ref={branch}"

    try:
        data = _api_request("GET", url, token, body=None)
        return data.get("sha")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise
    except RuntimeError as e:
        # _api_request wraps HTTPError as RuntimeError; handle 404 gracefully
        if "HTTP 404" in str(e):
            return None
        raise


def _api_request(
    method: str,
    url: str,
    token: str,
    body: dict | None,
) -> dict:
    """Make a JSON API request and return the parsed response."""
    data = json.dumps(body).encode() if body is not None else None
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try:
            body_text = e.read().decode(errors="replace")
        except Exception:
            body_text = ""
        raise RuntimeError(
            f"HTTP {e.code} {method} {url}: {body_text[:300]}"
        ) from e
