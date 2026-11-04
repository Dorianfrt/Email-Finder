#!/usr/bin/env python3
"""This program extract the author email address from a GitHub commit patch."""

from __future__ import annotations

import argparse
import re
import sys
from typing import Final
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen


EMAIL_PATTERN = re.compile(
    r"From:\s*[^<\r\n]*<(?P<email>[^>\s]+)>", re.IGNORECASE
)

GREEN: Final = "\033[92m"
CYAN: Final = "\033[96m"
RESET: Final = "\033[0m"


def print_result(email: str) -> None:
    use_color = sys.stdout.isatty()
    green = GREEN if use_color else ""
    cyan = CYAN if use_color else ""
    reset = RESET if use_color else ""

    print()
    print(f"{cyan}  EMAIL-FINDER v1.0{reset}")
    print("  -----------------")
    print(f"  {green}[+] Author email found{reset}")
    print(f"      {email}")
    print()


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
        help="URL du commit ou du patch à inspecter",
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
        print_result(extract_email(patch))
    except FinderError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
