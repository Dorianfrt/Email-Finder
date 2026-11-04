#!/usr/bin/env python3
"""Find author emails in the public repositories of a GitHub user."""

from __future__ import annotations

import argparse
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from patcher import PatcherError, extract_email, fetch_patch


GITHUB_API = "https://api.github.com"
USER_AGENT = "email-finder/1.0"


class GitHubError(RuntimeError):
    """Raised when the GitHub API cannot be queried."""


def github_get(path: str, params: dict[str, object], timeout: float) -> list[dict]:
    """Fetch one JSON list from the public GitHub API."""
    query = urlencode(params)
    url = f"{GITHUB_API}{path}?{query}" if query else f"{GITHUB_API}{path}"
    request = Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": USER_AGENT,
        },
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.load(response)
    except HTTPError as error:
        if error.code == 404:
            raise GitHubError("GitHub user or repository not found") from error
        if error.code == 403:
            raise GitHubError("GitHub API rate limit reached") from error
        raise GitHubError(f"GitHub API error ({error.code})") from error
    except (URLError, TimeoutError, json.JSONDecodeError) as error:
        raise GitHubError(f"unable to query GitHub: {error}") from error

    if not isinstance(payload, list):
        raise GitHubError("unexpected response from GitHub API")
    return payload


def get_public_repositories(username: str, timeout: float) -> list[dict]:
    """Return all public repositories owned by *username*."""
    repositories: list[dict] = []
    page = 1

    while True:
        batch = github_get(
            f"/users/{quote(username, safe='')}/repos",
            {"type": "owner", "per_page": 100, "page": page},
            timeout,
        )
        if not batch:
            return repositories
        repositories.extend(batch)
        page += 1


def get_repository_commits(
    owner: str, repository: str, username: str, timeout: float
) -> list[dict]:
    """Return commits authored by *username* in one public repository."""
    commits: list[dict] = []
    page = 1

    while True:
        batch = github_get(
            f"/repos/{quote(owner, safe='')}/{quote(repository, safe='')}/commits",
            {
                "author": username,
                "per_page": 100,
                "page": page,
            },
            timeout,
        )
        if not batch:
            return commits
        commits.extend(batch)
        page += 1


def scan_user(username: str, timeout: float) -> int:
    """Scan repositories and print unique author emails."""
    print("\n  GITHUB-FINDER v1.0")
    print("  -----------------")
    print(f"  [+] Target: {username}")

    repositories = get_public_repositories(username, timeout)
    print(f"  [+] Public repositories found: {len(repositories)}")

    emails: set[str] = set()
    commits_found = 0

    for repository in repositories:
        name = repository.get("name")
        owner = repository.get("owner", {}).get("login", username)
        if not name:
            continue

        try:
            commits = get_repository_commits(owner, name, username, timeout)
        except GitHubError as error:
            print(f"  [-] {owner}/{name}: {error}", file=sys.stderr)
            continue

        for commit in commits:
            patch_url = commit.get("html_url")
            if not patch_url:
                continue

            commits_found += 1
            try:
                email = extract_email(fetch_patch(patch_url, timeout))
            except PatcherError:
                continue
            emails.add(email)

    print(f"  [+] Commits inspected: {commits_found}")
    if emails:
        print("  [+] Emails found:")
        for email in sorted(emails):
            print(f"      {email}")
    else:
        print("  [-] No author email found")

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Find author emails in a GitHub user's public repositories."
    )
    parser.add_argument("username", help="nom d'utilisateur GitHub")
    parser.add_argument(
        "--timeout", type=float, default=10.0, help="timeout réseau en secondes"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return scan_user(args.username, args.timeout)
    except GitHubError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
