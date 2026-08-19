#!/usr/bin/env python3
"""Verify required routes and privacy boundaries in a built static site."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REQUIRED_ROUTES = (
    "index.html",
    "docs/index.html",
    "docs/getting-started/index.html",
    "docs/guides/index.html",
    "docs/guides/convert/compose-to-compose/index.html",
    "docs/guides/convert/compose-to-quadlet/index.html",
    "docs/guides/convert/quadlet-to-compose/index.html",
    "docs/guides/convert/quadlet-to-quadlet/index.html",
    "docs/concepts/index.html",
    "docs/reference/index.html",
    "docs/libraries/index.html",
    "docs/api/index.html",
    "docs/development/index.html",
)
REQUIRED_ASSETS = (
    "assets/images/favicon.svg",
    "assets/images/brand/boxferry-mark.svg",
    "assets/images/brand/boxferry-wordmark.svg",
    "assets/images/brand/generated/boxferry-mark-dark.svg",
    "assets/images/brand/generated/boxferry-mark-light.svg",
    "assets/images/brand/generated/boxferry-wordmark-dark.svg",
    "assets/images/brand/generated/boxferry-wordmark-light.svg",
    "assets/images/brand/generated/boxferry-social-dark.svg",
    "assets/images/brand/generated/boxferry-social-light.svg",
)
FORBIDDEN_FRAGMENTS = (
    "/home/",
    "/workspaces/",
    "temp/documentation-plan.md",
    "documentation-plan.md",
)


class SiteVerificationError(RuntimeError):
    """Describe an incomplete or privacy-unsafe static site."""


def verify_site(site_directory: Path) -> None:
    """Validate stable routes, source metadata, and path-disclosure boundaries."""
    site = site_directory.resolve()
    if not site.is_dir():
        raise SiteVerificationError(f"site directory does not exist: {site_directory}")

    missing = [route for route in REQUIRED_ROUTES if not (site / route).is_file()]
    if missing:
        raise SiteVerificationError(f"required public routes are missing: {', '.join(missing)}")

    missing_assets = [asset for asset in REQUIRED_ASSETS if not (site / asset).is_file()]
    if missing_assets:
        raise SiteVerificationError(
            f"required public assets are missing: {', '.join(missing_assets)}"
        )

    metadata_path = site / "assets" / "data" / "documentation-sources.json"
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SiteVerificationError(
            "documentation source metadata is missing or invalid"
        ) from error
    if metadata.get("schema_version") != 1:
        raise SiteVerificationError("documentation source metadata has an unknown schema")
    repositories = metadata.get("repositories")
    if not isinstance(repositories, list) or len(repositories) != 3:
        raise SiteVerificationError("documentation source metadata must contain three repositories")

    for path in sorted(site.rglob("*")):
        if path.is_symlink():
            raise SiteVerificationError(
                f"built site contains a symbolic link: {path.relative_to(site)}"
            )
        if not path.is_file() or path.suffix not in {
            ".css",
            ".html",
            ".js",
            ".json",
            ".svg",
            ".txt",
        }:
            continue
        content = path.read_text(encoding="utf-8", errors="replace")
        for fragment in FORBIDDEN_FRAGMENTS:
            if fragment in content:
                raise SiteVerificationError(
                    f"built site discloses a forbidden path fragment in {path.relative_to(site)}"
                )


def main() -> int:
    """Run static-site verification."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("site_directory", nargs="?", type=Path, default=Path("site"))
    arguments = parser.parse_args()
    try:
        verify_site(arguments.site_directory)
    except SiteVerificationError as error:
        print(f"boxferry-website: site verification failed: {error}", file=sys.stderr)
        return 1
    print("BoxFerry static site routes and privacy boundaries are valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
