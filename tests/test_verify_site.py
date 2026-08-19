"""Tests for generated-route and privacy verification."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.verify_site import (
    REQUIRED_ASSETS,
    REQUIRED_LINKS,
    REQUIRED_ROUTES,
    SiteVerificationError,
    verify_site,
)


class SiteVerificationTests(unittest.TestCase):
    """Ensure required routes and forbidden disclosure checks fail closed."""

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.site = Path(self.temporary_directory.name) / "site"
        for route in REQUIRED_ROUTES:
            path = self.site / route
            path.parent.mkdir(parents=True, exist_ok=True)
            links = "".join(f'<a href="{link}"></a>' for link in REQUIRED_LINKS)
            path.write_text(f"<!doctype html><title>BoxFerry</title>{links}\n", encoding="utf-8")
        for asset in REQUIRED_ASSETS:
            path = self.site / asset
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('<svg xmlns="http://www.w3.org/2000/svg" />\n', encoding="utf-8")
        metadata = self.site / "assets" / "data" / "documentation-sources.json"
        metadata.parent.mkdir(parents=True)
        metadata.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "repositories": [
                        {"name": "boxferry"},
                        {"name": "compose-lens"},
                        {"name": "quadlet-lens"},
                    ],
                }
            ),
            encoding="utf-8",
        )

    def test_complete_site_passes(self) -> None:
        verify_site(self.site)

    def test_missing_route_fails(self) -> None:
        (self.site / REQUIRED_ROUTES[-1]).unlink()

        with self.assertRaisesRegex(SiteVerificationError, "required public routes are missing"):
            verify_site(self.site)

    def test_missing_brand_asset_fails(self) -> None:
        (self.site / REQUIRED_ASSETS[-1]).unlink()

        with self.assertRaisesRegex(SiteVerificationError, "required public assets are missing"):
            verify_site(self.site)

    def test_missing_required_link_fails(self) -> None:
        homepage = self.site / "index.html"
        homepage.write_text(
            homepage.read_text(encoding="utf-8").replace(REQUIRED_LINKS[-1], ""),
            encoding="utf-8",
        )

        with self.assertRaisesRegex(SiteVerificationError, "required public links are missing"):
            verify_site(self.site)

    def test_host_path_disclosure_fails(self) -> None:
        homepage = self.site / "index.html"
        homepage.write_text(
            f"{homepage.read_text(encoding='utf-8')}/workspaces/private/source",
            encoding="utf-8",
        )

        with self.assertRaisesRegex(SiteVerificationError, "forbidden path fragment"):
            verify_site(self.site)

    def test_invalid_source_metadata_fails(self) -> None:
        metadata = self.site / "assets" / "data" / "documentation-sources.json"
        metadata.write_text("{}", encoding="utf-8")

        with self.assertRaisesRegex(SiteVerificationError, "unknown schema"):
            verify_site(self.site)


if __name__ == "__main__":
    unittest.main()
