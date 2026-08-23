"""Tests for deterministic production artifact preparation."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.prepare_deployment import (
    APACHE_POLICY,
    DEPLOYMENT_METADATA,
    RELEASE_MANIFEST,
    DeploymentPreparationError,
    prepare_deployment,
)

REVISION = "0123456789abcdef0123456789abcdef01234567"


class DeploymentPreparationTests(unittest.TestCase):
    """Keep generated server policy and release evidence reproducible."""

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.site = Path(self.temporary_directory.name) / "site"
        self.site.mkdir()

    def test_prepare_deployment_installs_exact_policy_and_metadata(self) -> None:
        actual_revision = prepare_deployment(self.site, revision=REVISION)

        self.assertEqual(actual_revision, REVISION)
        self.assertEqual(
            (self.site / ".htaccess").read_text(encoding="utf-8"),
            APACHE_POLICY.read_text(encoding="utf-8"),
        )
        self.assertEqual(
            (self.site / RELEASE_MANIFEST).read_text(encoding="utf-8"),
            f"schema-version=1\nrevision={REVISION}\n",
        )
        self.assertEqual(
            json.loads((self.site / DEPLOYMENT_METADATA).read_text(encoding="utf-8")),
            {
                "schema_version": 1,
                "website_revision": REVISION,
            },
        )

    def test_apache_policy_enforces_static_security_contract(self) -> None:
        policy = APACHE_POLICY.read_text(encoding="utf-8")

        for expected in (
            "Options -Indexes",
            "DirectoryIndex index.html",
            "AddType text/javascript .js .mjs",
            '<Files ".boxferry-release">',
            "Require all denied",
            "Content-Security-Policy",
            "Strict-Transport-Security",
            "X-Content-Type-Options",
            'Cache-Control "no-cache, max-age=0, must-revalidate"',
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, policy)

    def test_invalid_revision_is_rejected(self) -> None:
        with self.assertRaisesRegex(DeploymentPreparationError, "40 lowercase hex digits"):
            prepare_deployment(self.site, revision="main")

    def test_missing_site_is_rejected(self) -> None:
        self.site.rmdir()

        with self.assertRaisesRegex(DeploymentPreparationError, "site directory does not exist"):
            prepare_deployment(self.site, revision=REVISION)


if __name__ == "__main__":
    unittest.main()
