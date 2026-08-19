#!/usr/bin/env python3
"""Verify required routes and privacy boundaries in a built static site."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REQUIRED_ROUTES = (
    "index.html",
    "legal-notice/index.html",
    "privacy-policy/index.html",
    "docs/index.html",
    "docs/getting-started/index.html",
    "docs/guides/index.html",
    "docs/guides/convert/compose-to-compose/index.html",
    "docs/guides/convert/compose-to-quadlet/index.html",
    "docs/guides/convert/quadlet-to-compose/index.html",
    "docs/guides/convert/quadlet-to-quadlet/index.html",
    "docs/concepts/index.html",
    "docs/reference/index.html",
    "docs/reference/cli/index.html",
    "docs/reference/diagnostics/index.html",
    "docs/reference/compatibility/index.html",
    "docs/reference/error-reports/index.html",
    "docs/libraries/index.html",
    "docs/libraries/compose-lens/index.html",
    "docs/libraries/compose-lens/model/index.html",
    "docs/libraries/compose-lens/parsing-rendering/index.html",
    "docs/libraries/compose-lens/diagnostics/index.html",
    "docs/libraries/compose-lens/compatibility/index.html",
    "docs/libraries/quadlet-lens/index.html",
    "docs/libraries/quadlet-lens/model/index.html",
    "docs/libraries/quadlet-lens/parsing-rendering/index.html",
    "docs/libraries/quadlet-lens/diagnostics/index.html",
    "docs/libraries/quadlet-lens/compatibility/index.html",
    "docs/api/index.html",
    "docs/api/compose-lens/index.html",
    "docs/api/compose-lens/compose_lens/index.html",
    "docs/api/quadlet-lens/index.html",
    "docs/api/quadlet-lens/quadlet_lens/index.html",
    "docs/development/index.html",
    "docs/development/architecture/index.html",
    "docs/development/rust-api/index.html",
    "docs/development/testing/index.html",
    "docs/development/contributing/index.html",
    "docs/development/releases/index.html",
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
    "docs/reference/diagnostics/rules.json",
    "docs/libraries/quadlet-lens/catalogue/v1/podman-supported-range.toml",
    "search.json",
)
REQUIRED_LINKS = (
    "https://github.com/Strukturpiloten/boxferry",
    "https://www.strukturpiloten.de/",
    "./legal-notice/",
    "./privacy-policy/",
    "https://www.strukturpiloten.de/kontakt",
)
FORBIDDEN_FRAGMENTS = (
    "/home/",
    "/workspaces/",
    "temp/documentation-plan.md",
    "documentation-plan.md",
)


class SiteVerificationError(RuntimeError):
    """Describe an incomplete or privacy-unsafe static site."""


def _verify_rule_routes_and_search(site: Path) -> None:
    catalogue_path = site / "docs" / "reference" / "diagnostics" / "rules.json"
    try:
        catalogue = json.loads(catalogue_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SiteVerificationError("diagnostic rule catalogue is missing or invalid") from error
    rules = catalogue.get("rules")
    if catalogue.get("schema_version") != 1 or not isinstance(rules, list) or not rules:
        raise SiteVerificationError("diagnostic rule catalogue has an invalid contract")

    search_text = (site / "search.json").read_text(encoding="utf-8")
    for rule in rules:
        if not isinstance(rule, dict):
            raise SiteVerificationError("diagnostic rule catalogue contains an invalid rule")
        code = rule.get("code")
        name = rule.get("name")
        if not isinstance(code, str) or not re.fullmatch(r"(?:BFC|BFQ|BFO)[0-9]{4}", code):
            raise SiteVerificationError("diagnostic rule catalogue contains an invalid code")
        if not isinstance(name, str) or not name:
            raise SiteVerificationError(f"diagnostic rule {code} has no name")
        page = site / "docs" / "reference" / "diagnostics" / "rules" / code / "index.html"
        if not page.is_file():
            raise SiteVerificationError(f"diagnostic rule route is missing: {code}")
        page_text = page.read_text(encoding="utf-8")
        if code not in page_text or name not in page_text:
            raise SiteVerificationError(f"diagnostic rule route content drifted: {code}")
        if code not in search_text or name not in search_text:
            raise SiteVerificationError(f"diagnostic rule is missing from generated search: {code}")


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

    if (site / "_data" / "documentation-examples.toml").exists():
        raise SiteVerificationError("assembly-only documentation example data was published")

    for slug, crate in (("compose-lens", "compose_lens"), ("quadlet-lens", "quadlet_lens")):
        redirect = (site / "docs" / "api" / slug / "index.html").read_text(encoding="utf-8")
        if f"url={crate}/" not in redirect or f'href="{crate}/"' not in redirect:
            raise SiteVerificationError(f"Rustdoc entry route is not a valid redirect: {slug}")

    _verify_rule_routes_and_search(site)

    homepage = (site / "index.html").read_text(encoding="utf-8")
    missing_links = [link for link in REQUIRED_LINKS if f'href="{link}"' not in homepage]
    if missing_links:
        raise SiteVerificationError(
            f"required public links are missing: {', '.join(missing_links)}"
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
