#!/usr/bin/env python3
"""Extract the author email address from a GitHub commit patch."""

from __future__ import annotations

import argparse
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen


DEFAULT_PATCH_URL = (
    "https://github.com/Dorianfrt/Dataleon-Back-end-Test-case/commit/"
    "cf75e2b95a1783ef0a7673df710ff97e4b63851d.patch"
)
EMAIL_PATTERN = re.compile(
    r"From:\s*[^<\r\n]*<(?P<email>[^>\s]+)>", re.IGNORECASE
)


class FinderError(RuntimeError):
    """Raised when the patch cannot be downloaded or parsed."""


def normalize_patch_url(url: str) -> str:
    """Add the ``.patch`` suffix when it is missing from *url*."""
    parts = urlsplit(url)
    path = parts.path.rstrip("/")

    if not path.lower().endswith(".patch"):
        path += ".patch"

    return urlunsplit((parts.scheme, parts.netloc, path, parts.query, parts.fragment))


def fetch_patch(url: str, timeout: float = 10.0) -> str:
    """Download and decode a patch from *url*."""
    request = Request(
        normalize_patch_url(url),
        headers={"User-Agent": "email-finder/1.0"},
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            return response.read().decode("utf-8", errors="replace")
    except (HTTPError, URLError, TimeoutError) as error:
        raise FinderError(f"unable to download patch: {error}") from error


def extract_email(patch: str) -> str:
    """Return the first author email found in a patch header."""
    match = EMAIL_PATTERN.search(patch)
    if not match:
        raise FinderError("no author email found in the patch")
    return match.group("email")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract an author email address from a GitHub commit patch."
    )
    parser.add_argument(
        "url",
        nargs="?",
        default=DEFAULT_PATCH_URL,
        help="URL of the patch to inspect (default: the original example URL)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="download timeout in seconds (default: 10)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        patch = fetch_patch(args.url, timeout=args.timeout)
        print(extract_email(patch))
    except FinderError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
