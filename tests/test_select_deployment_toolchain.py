"""Preserve legacy rebuild metadata and reject unsupported toolchain substitutions."""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.select_deployment_toolchain import select_toolchain, verify_checkout

ROOT = Path(__file__).resolve().parents[1]
HISTORICAL = ROOT / "deployment/historical-uv.json"


class DeploymentToolchainTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.source = Path(temporary.name)
        self.project = self.source / "pyproject.toml"
        self.project.write_text('[tool.uv]\nrequired-version = "==0.13.5"\n', encoding="utf-8")
        self.python = self.source / ".python-version"
        self.python.write_text("3.14\n", encoding="utf-8")

    def select(self, **platform: str) -> dict[str, str]:
        return select_toolchain(
            self.source,
            HISTORICAL,
            system=platform.get("system", "Linux"),
            architecture=platform.get("architecture", "x86_64"),
        )

    def manifest(self, **changes: object) -> None:
        directory = self.source / ".github"
        directory.mkdir(exist_ok=True)
        (directory / "automation.json").write_text(
            json.dumps(
                {
                    "schema": 1,
                    "interface": 1,
                    "repository": "Strukturpiloten/boxferry",
                    "revision": "b" * 40,
                    "policy": "scripts/validation-policy.json",
                    **changes,
                }
            ),
            encoding="utf-8",
        )

    def test_baseline_exact_legacy_uv_and_source_python_remain_authoritative(self) -> None:
        marker = self.source / "must-not-run"
        (self.source / "setup.py").write_text(
            f"from pathlib import Path\nPath({str(marker)!r}).touch()\n", encoding="utf-8"
        )
        selected = self.select()
        self.assertEqual(selected["mode"], "legacy")
        self.assertEqual(selected["legacy_version"], "0.13.5")
        self.assertEqual(
            selected["legacy_checksum"],
            "f68d291c75783122dad58ab77def0e13f3233f358731db5d6d7e8715603b928f",
        )
        self.assertEqual(self.python.read_text(encoding="utf-8"), "3.14\n")
        self.assertNotIn("python_version", selected)
        self.assertFalse(marker.exists())

    def test_missing_ranged_unknown_and_malformed_legacy_constraints_are_rejected(self) -> None:
        for content in (
            "[project]\nname = 'legacy'\n",
            "[tool.uv]\nrequired-version = '>=0.13.5'\n",
            "[tool.uv]\nrequired-version = '==0.13.6'\n",
            "tool = 'invalid'\n",
            "[tool]\nuv = 'invalid'\n",
            "invalid TOML!",
        ):
            with self.subTest(content=content), self.assertRaises(ValueError):
                self.project.write_text(content, encoding="utf-8")
                self.select()

    def test_new_source_uses_its_own_exact_manifest_without_legacy_fallback(self) -> None:
        self.manifest()
        self.project.write_text(
            "Not TOML and must not be read for canonical selection.", encoding="utf-8"
        )
        self.assertEqual(self.select(), {"mode": "canonical", "automation_sha": "b" * 40})

    def test_bad_manifest_cannot_fall_back_to_an_otherwise_valid_legacy_declaration(self) -> None:
        for invalid in (
            {"revision": "main"},
            {"repository": "elsewhere/project"},
            {"interface": 2},
            {"schema": True},
            {"policy": "../other.json"},
        ):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                self.manifest(**invalid)
                self.select()

    def test_unsupported_platform_and_symlinked_metadata_fail_closed(self) -> None:
        for platform in ({"system": "Darwin"}, {"architecture": "aarch64"}):
            with self.subTest(platform=platform), self.assertRaises(ValueError):
                self.select(**platform)
        self.project.unlink()
        self.project.symlink_to(self.python)
        with self.assertRaises(ValueError):
            self.select()

    def test_ambiguous_duplicate_manifest_fields_are_rejected(self) -> None:
        self.manifest()
        manifest = self.source / ".github/automation.json"
        text = manifest.read_text(encoding="utf-8")
        manifest.write_text(text[:-1] + ', "revision": "' + "c" * 40 + '"}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "repeats a field"):
            self.select()

    def test_bad_historical_integrity_cannot_select_a_legacy_archive(self) -> None:
        record = json.loads(HISTORICAL.read_text(encoding="utf-8"))
        record["assets"]["Linux-x86_64"]["sha256"] = "not-a-sha256"
        invalid = self.source / "invalid-record.json"
        invalid.write_text(json.dumps(record), encoding="utf-8")
        with self.assertRaises(ValueError):
            select_toolchain(self.source, invalid, system="Linux", architecture="x86_64")

    def test_checkout_must_match_the_approved_exact_source_revision(self) -> None:
        with patch("scripts.select_deployment_toolchain.subprocess.run") as run:
            run.return_value = subprocess.CompletedProcess([], 0, "a" * 40 + "\n", "")
            verify_checkout(self.source, "a" * 40)
            with self.assertRaises(ValueError):
                verify_checkout(self.source, "b" * 40)
            run.reset_mock()
            with self.assertRaises(ValueError):
                verify_checkout(self.source, "main")
            run.assert_not_called()

    def test_workflow_keeps_discovery_trusted_and_legacy_python_unmodified(self) -> None:
        workflow = (ROOT / ".github/workflows/deploy.yml").read_text(encoding="utf-8")
        self.assertIn("ref: ${{ github.sha }}\n          path: _deployment_policy", workflow)
        self.assertIn("python3 _deployment_policy/scripts/select_deployment_toolchain.py", workflow)
        self.assertIn("ref: ${{ steps.toolchain.outputs.automation_sha }}", workflow)
        self.assertIn("version-file: source/pyproject.toml", workflow)
        self.assertIn("checksum: ${{ steps.toolchain.outputs.legacy_checksum }}", workflow)
        self.assertIn("download-from-astral-mirror: false", workflow)
        self.assertNotIn("python-version:", workflow)
        self.assertNotIn("UV_PYTHON:", workflow)
        self.assertIn("--source-root source", workflow)
        self.assertIn("working-directory: source", workflow)
        self.assertIn("path: source/site/", workflow)
        rollback = workflow.split("\n  rollback:\n", 1)[1]
        self.assertNotIn("needs: [request, build]", rollback)
        self.assertNotIn("setup-uv", rollback)
