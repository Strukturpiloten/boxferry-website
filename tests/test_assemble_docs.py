"""Positive and negative tests for deterministic documentation assembly."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.assemble_docs import AssemblyError, assemble, load_manifest

REVISION = "0123456789abcdef0123456789abcdef01234567"


class AssemblyTests(unittest.TestCase):
    """Exercise source copying and fail-closed path validation."""

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name)
        self.website = self.root / "website"
        self.source = self.root / "source"
        (self.website / "content" / "docs").mkdir(parents=True)
        (self.website / "content" / "index.md").write_text("# Home\n", encoding="utf-8")
        (self.source / ".git").mkdir(parents=True)
        (self.source / "docs").mkdir(parents=True)
        (self.source / "docs" / "guide.md").write_text("# Imported\n", encoding="utf-8")

    def write_manifest(
        self,
        *,
        source: str = "docs/guide.md",
        destination: str = "docs/imported.md",
        revision: str = REVISION,
        duplicate: bool = False,
    ) -> Path:
        duplicate_mapping = ""
        if duplicate:
            duplicate_mapping = f'''\n[[repositories.documents]]
source = "docs/guide.md"
destination = "{destination}"
'''
        manifest = self.website / "documentation-sources.toml"
        manifest.write_text(
            f'''schema-version = 1

[site]
content-directory = "content"
staging-directory = ".generated/docs"

[[repositories]]
name = "boxferry"
repository = "https://github.com/Strukturpiloten/boxferry.git"
revision = "{revision}"
local-directories = ["../source"]

[[repositories.documents]]
source = "{source}"
destination = "{destination}"
{duplicate_mapping}''',
            encoding="utf-8",
        )
        return manifest

    def test_local_assembly_copies_owned_and_explicit_external_content(self) -> None:
        manifest = load_manifest(self.write_manifest())

        staging = assemble(manifest, "local")

        self.assertEqual((staging / "index.md").read_text(encoding="utf-8"), "# Home\n")
        self.assertEqual(
            (staging / "docs" / "imported.md").read_text(encoding="utf-8"),
            "# Imported\n",
        )
        metadata = json.loads(
            (staging / "assets" / "data" / "documentation-sources.json").read_text(encoding="utf-8")
        )
        self.assertEqual(metadata["repositories"][0]["revision"], REVISION)
        self.assertNotIn(str(self.root), json.dumps(metadata))

    def test_parent_traversal_and_absolute_destinations_are_rejected(self) -> None:
        for destination in ("../escape.md", "/escape.md", "docs\\escape.md"):
            with self.subTest(destination=destination), self.assertRaises(AssemblyError):
                load_manifest(self.write_manifest(destination=destination))

    def test_parent_traversal_and_absolute_sources_are_rejected(self) -> None:
        for source in ("../secret", "/secret", "docs\\secret"):
            with self.subTest(source=source), self.assertRaises(AssemblyError):
                load_manifest(self.write_manifest(source=source))

    def test_duplicate_destinations_are_rejected(self) -> None:
        with self.assertRaisesRegex(AssemblyError, "duplicate documentation destination"):
            load_manifest(self.write_manifest(duplicate=True))

    def test_non_exact_revision_is_rejected(self) -> None:
        with self.assertRaisesRegex(AssemblyError, "40-character Git SHA"):
            load_manifest(self.write_manifest(revision="main"))

    def test_symlinked_document_is_rejected(self) -> None:
        (self.source / "docs" / "guide.md").unlink()
        (self.source / "docs" / "guide.md").symlink_to(self.website / "content" / "index.md")
        manifest = load_manifest(self.write_manifest())

        with self.assertRaisesRegex(AssemblyError, "symbolic links"):
            assemble(manifest, "local")

    def test_missing_local_checkout_is_actionable(self) -> None:
        manifest_path = self.write_manifest()
        for child in sorted(self.source.rglob("*"), reverse=True):
            if child.is_file():
                child.unlink()
            else:
                child.rmdir()
        self.source.rmdir()
        manifest = load_manifest(manifest_path)

        with self.assertRaisesRegex(AssemblyError, "local source repository is missing"):
            assemble(manifest, "local")


if __name__ == "__main__":
    unittest.main()
