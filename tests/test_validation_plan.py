"""Regression tests for the conservative website maintenance profile."""

from __future__ import annotations

import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validation-plan.py"
SPEC = importlib.util.spec_from_file_location("website_validation_plan", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
plan = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(plan)


class ValidationPlanTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.git("init", "-q")
        self.git("config", "user.name", "Test")
        self.git("config", "user.email", "test@example.invalid")
        (self.root / "README.md").write_text("# Before\n", encoding="utf-8")
        (self.root / "content").mkdir()
        (self.root / "content" / "index.md").write_text("# Site\n", encoding="utf-8")
        self.git("add", ".")
        self.git("commit", "-qm", "baseline")
        self.base = self.git("rev-parse", "HEAD").strip()

    def git(self, *arguments: str) -> str:
        return subprocess.check_output(["git", *arguments], cwd=self.root, text=True)

    def test_modified_maintenance_prose_gets_small_profile(self) -> None:
        (self.root / "README.md").write_text("# After\n", encoding="utf-8")
        self.assertEqual(plan.profile(self.root, self.base, None), "maintenance")
        self.git("add", "README.md")
        self.git("commit", "-qm", "docs")
        self.assertEqual(
            plan.profile(self.root, self.base, self.git("rev-parse", "HEAD").strip()), "maintenance"
        )

    def test_site_content_and_mixed_changes_get_full_profile(self) -> None:
        (self.root / "content" / "index.md").write_text("# Changed site\n", encoding="utf-8")
        self.assertEqual(plan.profile(self.root, self.base, None), "full")
        (self.root / "README.md").write_text("# After\n", encoding="utf-8")
        self.assertEqual(plan.profile(self.root, self.base, None), "full")

    def test_untracked_and_renamed_files_get_full_profile(self) -> None:
        (self.root / "README.md").write_text("# After\n", encoding="utf-8")
        (self.root / "untracked.txt").write_text("unknown\n", encoding="utf-8")
        self.assertEqual(plan.profile(self.root, self.base, None), "full")
        (self.root / "untracked.txt").unlink()
        (self.root / "docs").mkdir()
        self.git("mv", "README.md", "docs/architecture.md")
        self.assertEqual(plan.profile(self.root, self.base, None), "full")

    def test_symlink_and_wrong_revision_get_full_profile(self) -> None:
        (self.root / "README.md").unlink()
        (self.root / "README.md").symlink_to("content/index.md")
        self.assertEqual(plan.profile(self.root, self.base, None), "full")
        self.git("add", "README.md")
        self.git("commit", "-qm", "link")
        self.assertEqual(
            plan.profile(self.root, self.base, self.git("rev-parse", "HEAD").strip()), "full"
        )
        self.assertEqual(plan.profile(self.root, self.base, "0" * 40), "full")

    def test_add_delete_and_bad_diff_records_get_full_profile(self) -> None:
        for raw in (
            b"",
            b"M\0README.md",
            b"A\0README.md\0",
            b"D\0README.md\0",
            b"R100\0README.md\0docs/architecture.md\0",
        ):
            self.assertIsNone(plan.classified_paths(raw))
        self.assertEqual(plan.profile(self.root, self.base, None), "full")


if __name__ == "__main__":
    unittest.main()
