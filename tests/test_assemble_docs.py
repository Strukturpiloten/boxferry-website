"""Positive and negative tests for deterministic documentation assembly."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.assemble_docs import (
    AssemblyError,
    _generate_rule_reference,
    _verify_documented_commands,
    _verify_public_content,
    assemble,
    load_manifest,
)

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

    def test_rule_reference_is_generated_from_checked_catalogue(self) -> None:
        staging = self.root / "rules"
        diagnostics = staging / "docs" / "reference" / "diagnostics"
        diagnostics.mkdir(parents=True)
        (diagnostics / "index.md").write_text(
            "# Rules\n\n<!-- boxferry-generated-rule-index -->\n",
            encoding="utf-8",
        )
        (diagnostics / "rules.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "rules": [
                        {
                            "code": "BFC0001",
                            "name": "compose-model-invalid",
                            "default_severity": "error",
                            "description": "The value is invalid.",
                            "help": "Correct the value.",
                            "owner": "Compose adapter",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        _generate_rule_reference(staging)

        index = (diagnostics / "index.md").read_text(encoding="utf-8")
        page = (diagnostics / "rules" / "BFC0001" / "index.md").read_text(encoding="utf-8")
        self.assertIn("rules/BFC0001/", index)
        self.assertIn("# BFC0001: compose-model-invalid", page)
        self.assertIn("Correct the value.", page)

    def test_invalid_rule_catalogue_fails_before_generation(self) -> None:
        staging = self.root / "invalid-rules"
        diagnostics = staging / "docs" / "reference" / "diagnostics"
        diagnostics.mkdir(parents=True)
        (diagnostics / "index.md").write_text(
            "# Rules\n\n<!-- boxferry-generated-rule-index -->\n",
            encoding="utf-8",
        )
        (diagnostics / "rules.json").write_text(
            '{"schema_version":1,"rules":[{"code":"unsafe","name":"rule",'
            '"default_severity":"error","description":"Bad.","help":"Fix.",'
            '"owner":"Owner"}]}',
            encoding="utf-8",
        )

        with self.assertRaisesRegex(AssemblyError, "not a BoxFerry rule code"):
            _generate_rule_reference(staging)

    def test_documented_command_contract_requires_positive_and_negative_route_examples(
        self,
    ) -> None:
        staging = self.root / "examples"
        page = staging / "docs" / "guides" / "index.md"
        page.parent.mkdir(parents=True)
        page.write_text(
            "# Guide\n\n<!-- boxferry-example: only-one -->\n\n"
            "```console\nboxferry convert compose compose\n```\n",
            encoding="utf-8",
        )
        data = staging / "_data"
        data.mkdir()
        (data / "documentation-examples.toml").write_text(
            """schema = 1
fixture-directory = "fixtures"

[[examples]]
id = "only-one"
pages = ["docs/public/guides/index.md"]
command = "boxferry convert compose compose"
args = ["convert", "compose", "compose"]
expected-exit = 0
""",
            encoding="utf-8",
        )

        with self.assertRaisesRegex(AssemblyError, "every document route"):
            _verify_documented_commands(staging)

    def test_public_content_rejects_placeholder_copy(self) -> None:
        staging = self.root / "content-quality"
        page = staging / "docs" / "index.md"
        page.parent.mkdir(parents=True)
        page.write_text("# Docs\n\nThis guide will explain the command.\n", encoding="utf-8")

        with self.assertRaisesRegex(AssemblyError, "placeholder phrase"):
            _verify_public_content(staging)


if __name__ == "__main__":
    unittest.main()
