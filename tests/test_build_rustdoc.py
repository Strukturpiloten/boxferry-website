"""Tests for first-party Rust API generation."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.assemble_docs import AssemblyError, load_manifest
from scripts.build_rustdoc import build_rustdoc

REVISION = "0123456789abcdef0123456789abcdef01234567"


class RustdocBuildTests(unittest.TestCase):
    """Keep generated API routes deterministic and fail closed."""

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name)
        self.website = self.root / "website"
        self.source = self.root / "compose-lens"
        self.podman_source = self.root / "podman-lens"
        self.site = self.website / "site"
        self.website.mkdir()
        self.site.mkdir()
        (self.source / ".git").mkdir(parents=True)
        (self.podman_source / ".git").mkdir(parents=True)
        self.manifest_path = self.website / "documentation-sources.toml"
        self.manifest_path.write_text(
            f'''schema-version = 1

[site]
content-directory = "content"
staging-directory = ".generated/docs"

[[repositories]]
name = "compose-lens"
repository = "https://github.com/Strukturpiloten/compose-lens.git"
revision = "{REVISION}"
local-directories = ["../compose-lens"]

[repositories.rustdoc]
package = "compose-lens"
crate = "compose_lens"
destination = "docs/api/compose-lens"

[[repositories]]
name = "podman-lens"
repository = "https://github.com/Strukturpiloten/podman-lens.git"
revision = "{REVISION}"
local-directories = ["../podman-lens"]

[repositories.rustdoc]
package = "podman-lens"
crate = "podman_lens"
destination = "docs/api/podman-lens"
''',
            encoding="utf-8",
        )

    @staticmethod
    def _generate_declared_crate(arguments: list[str], **_: object) -> None:
        target = Path(arguments[arguments.index("--target-dir") + 1]) / "doc"
        package = arguments[arguments.index("--package") + 1]
        crate = target / package.replace("-", "_")
        crate.mkdir(parents=True)
        (crate / "index.html").write_text(f"<!doctype html>{package} API\n", encoding="utf-8")

    def test_build_copies_complete_rustdoc_and_adds_stable_redirect(self) -> None:
        manifest = load_manifest(self.manifest_path)

        with patch(
            "scripts.build_rustdoc.subprocess.run", side_effect=self._generate_declared_crate
        ):
            build_rustdoc(manifest, "local", self.site)

        destination = self.site / "docs" / "api" / "compose-lens"
        self.assertTrue((destination / "compose_lens" / "index.html").is_file())
        redirect = (destination / "index.html").read_text(encoding="utf-8")
        self.assertIn("url=compose_lens/", redirect)
        self.assertIn('href="compose_lens/"', redirect)

        podman_destination = self.site / "docs" / "api" / "podman-lens"
        self.assertTrue((podman_destination / "podman_lens" / "index.html").is_file())
        podman_redirect = (podman_destination / "index.html").read_text(encoding="utf-8")
        self.assertIn("url=podman_lens/", podman_redirect)
        self.assertIn('href="podman_lens/"', podman_redirect)

    def test_missing_declared_crate_output_is_actionable(self) -> None:
        manifest = load_manifest(self.manifest_path)

        with (
            patch("scripts.build_rustdoc.subprocess.run", return_value=None),
            self.assertRaisesRegex(AssemblyError, "declared crate `compose_lens`"),
        ):
            build_rustdoc(manifest, "local", self.site)


if __name__ == "__main__":
    unittest.main()
