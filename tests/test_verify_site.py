"""Tests for generated-route and privacy verification."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.prepare_deployment import prepare_deployment
from scripts.verify_site import (
    REQUIRED_ASSETS,
    REQUIRED_LINKS,
    REQUIRED_ROUTES,
    REQUIRED_SUPPORT_LINKS,
    RUSTDOC_ROUTES,
    SOURCE_MANIFEST_LINK,
    SOURCE_REPOSITORIES,
    SiteVerificationError,
    verify_site,
)

REVISION = "0123456789abcdef0123456789abcdef01234567"


class SiteVerificationTests(unittest.TestCase):
    """Ensure required routes and forbidden disclosure checks fail closed."""

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.site = Path(self.temporary_directory.name) / "site"
        for route in REQUIRED_ROUTES:
            path = self.site / route
            path.parent.mkdir(parents=True, exist_ok=True)
            links = "".join(
                f'<a href="{link}"></a>'
                for link in (*REQUIRED_LINKS, *REQUIRED_SUPPORT_LINKS, SOURCE_MANIFEST_LINK)
            )
            path.write_text(f"<!doctype html><title>BoxFerry</title>{links}\n", encoding="utf-8")
        for asset in REQUIRED_ASSETS:
            path = self.site / asset
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('<svg xmlns="http://www.w3.org/2000/svg" />\n', encoding="utf-8")
        for slug, crate in RUSTDOC_ROUTES:
            redirect = self.site / "docs" / "api" / slug / "index.html"
            redirect.write_text(
                f'<meta http-equiv="refresh" content="0; url={crate}/">'
                f'<a href="{crate}/">API</a>\n',
                encoding="utf-8",
            )
        metadata = self.site / "assets" / "data" / "documentation-sources.json"
        metadata.parent.mkdir(parents=True)
        metadata.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "repositories": [
                        {
                            "name": name,
                            "repository": f"https://github.com/Strukturpiloten/{name}.git",
                            "revision": "0123456789abcdef0123456789abcdef01234567",
                        }
                        for name in SOURCE_REPOSITORIES
                    ],
                }
            ),
            encoding="utf-8",
        )
        catalogue = self.site / "docs" / "reference" / "diagnostics" / "rules.json"
        catalogue.parent.mkdir(parents=True, exist_ok=True)
        catalogue.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "rules": [
                        {
                            "code": "BFC0001",
                            "name": "compose-model-invalid",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        rule_page = (
            self.site / "docs" / "reference" / "diagnostics" / "rules" / "BFC0001" / "index.html"
        )
        rule_page.parent.mkdir(parents=True)
        rule_page.write_text(
            "<!doctype html><title>BFC0001</title>compose-model-invalid\n",
            encoding="utf-8",
        )
        search = self.site / "search.json"
        search.write_text(
            '{"docs":[{"title":"BFC0001: compose-model-invalid"}]}\n',
            encoding="utf-8",
        )
        prepare_deployment(self.site, revision=REVISION)

    def test_complete_site_passes(self) -> None:
        verify_site(self.site)

    def test_missing_route_fails(self) -> None:
        (self.site / REQUIRED_ROUTES[-1]).unlink()

        with self.assertRaisesRegex(SiteVerificationError, "required public routes are missing"):
            verify_site(self.site)

    def test_missing_apache_policy_fails(self) -> None:
        (self.site / ".htaccess").unlink()

        with self.assertRaisesRegex(SiteVerificationError, "Apache deployment policy is missing"):
            verify_site(self.site)

    def test_stale_apache_policy_fails(self) -> None:
        (self.site / ".htaccess").write_text("Options Indexes\n", encoding="utf-8")

        with self.assertRaisesRegex(SiteVerificationError, "Apache deployment policy is stale"):
            verify_site(self.site)

    def test_invalid_release_manifest_fails(self) -> None:
        (self.site / ".boxferry-release").write_text("revision=main\n", encoding="utf-8")

        with self.assertRaisesRegex(SiteVerificationError, "invalid contract"):
            verify_site(self.site)

    def test_mismatched_deployment_metadata_fails(self) -> None:
        metadata = self.site / "assets" / "data" / "deployment.json"
        metadata.write_text(
            json.dumps({"schema_version": 1, "website_revision": "f" * 40}),
            encoding="utf-8",
        )

        with self.assertRaisesRegex(SiteVerificationError, "does not match"):
            verify_site(self.site)

    def test_remote_font_resource_fails(self) -> None:
        homepage = self.site / "index.html"
        homepage.write_text(
            homepage.read_text(encoding="utf-8")
            + '<link href="https://fonts.googleapis.com/css?family=Inter">\n',
            encoding="utf-8",
        )

        with self.assertRaisesRegex(SiteVerificationError, "forbidden path fragment"):
            verify_site(self.site)

    def test_missing_brand_asset_fails(self) -> None:
        (self.site / REQUIRED_ASSETS[-3]).unlink()

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

    def test_missing_support_link_fails(self) -> None:
        support = self.site / "support" / "index.html"
        support.write_text(
            support.read_text(encoding="utf-8").replace(REQUIRED_SUPPORT_LINKS[0], ""),
            encoding="utf-8",
        )

        with self.assertRaisesRegex(SiteVerificationError, "required support links are missing"):
            verify_site(self.site)

    def test_missing_source_metadata_link_fails(self) -> None:
        sources = self.site / "docs" / "sources" / "index.html"
        sources.write_text(
            sources.read_text(encoding="utf-8").replace(SOURCE_MANIFEST_LINK, ""),
            encoding="utf-8",
        )

        with self.assertRaisesRegex(SiteVerificationError, "does not link to source metadata"):
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

    def test_incomplete_source_repository_set_fails(self) -> None:
        metadata = self.site / "assets" / "data" / "documentation-sources.json"
        document = json.loads(metadata.read_text(encoding="utf-8"))
        document["repositories"] = [
            repository
            for repository in document["repositories"]
            if repository["name"] != "podman-lens"
        ]
        metadata.write_text(json.dumps(document), encoding="utf-8")

        with self.assertRaisesRegex(SiteVerificationError, "incomplete or unordered"):
            verify_site(self.site)

    def test_invalid_source_revision_fails(self) -> None:
        metadata = self.site / "assets" / "data" / "documentation-sources.json"
        document = json.loads(metadata.read_text(encoding="utf-8"))
        document["repositories"][0]["revision"] = "main"
        metadata.write_text(json.dumps(document), encoding="utf-8")

        with self.assertRaisesRegex(SiteVerificationError, "revision is invalid"):
            verify_site(self.site)

    def test_missing_generated_rule_route_fails(self) -> None:
        (
            self.site / "docs" / "reference" / "diagnostics" / "rules" / "BFC0001" / "index.html"
        ).unlink()

        with self.assertRaisesRegex(SiteVerificationError, "rule route is missing"):
            verify_site(self.site)

    def test_rule_missing_from_search_fails(self) -> None:
        (self.site / "search.json").write_text('{"docs":[]}\n', encoding="utf-8")

        with self.assertRaisesRegex(SiteVerificationError, "missing from generated search"):
            verify_site(self.site)

    def test_invalid_rustdoc_redirect_fails(self) -> None:
        redirect = self.site / "docs" / "api" / "podman-lens" / "index.html"
        redirect.write_text('<a href="elsewhere/">Wrong API</a>\n', encoding="utf-8")

        with self.assertRaisesRegex(SiteVerificationError, "not a valid redirect"):
            verify_site(self.site)


if __name__ == "__main__":
    unittest.main()
