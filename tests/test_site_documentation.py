"""Verify the prose task retains strict builds without running Rust or deployment."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class SiteDocumentationTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / "scripts").mkdir()
        shutil.copy2(ROOT / "scripts/check-site-docs.sh", self.root / "scripts")
        (self.root / "README.md").write_text("# Documentation\n", encoding="utf-8")
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.log = self.root / "commands.log"
        mock = self.bin / "mock"
        mock.write_text(
            "#!/usr/bin/env bash\n"
            'printf "%s\\n" "${0##*/} $*" >> "${TASK_LOG}"\n'
            'if [[ "${0##*/} $*" == "${FAIL_COMMAND:-}" ]]; then exit 17; fi\n'
            'if [[ "${0##*/}" == git && "$1" == ls-files ]]; then printf "README.md\\0"; fi\n',
            encoding="utf-8",
        )
        mock.chmod(0o755)
        for tool in ("npm", "uv", "prettier", "markdownlint-cli2", "cspell", "lychee", "git"):
            (self.bin / tool).symlink_to(mock)

    def run_task(self, **environment: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(self.root / "scripts/check-site-docs.sh")],
            env={
                **os.environ,
                "PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}",
                "TASK_LOG": str(self.log),
                "BOXFERRY_WEBSITE_SOURCE_MODE": "locked",
                "BOXFERRY_WEBSITE_SHARED_TOOLS": "1",
                **environment,
            },
            capture_output=True,
            text=True,
            check=False,
        )

    def test_public_prose_keeps_safe_assembly_and_strict_rendering(self) -> None:
        result = self.run_task()
        self.assertEqual(result.returncode, 0, result.stderr)
        commands = self.log.read_text(encoding="utf-8").splitlines()
        self.assertIn(
            "uv run --frozen python scripts/assemble_docs.py --source-mode locked", commands
        )
        self.assertIn("uv run --frozen zensical build --clean --strict", commands)
        self.assertIn("uv run --frozen python scripts/publish_ai_docs.py", commands)
        self.assertFalse(any("rustdoc" in command or "deploy" in command for command in commands))

    def test_failed_strict_render_is_not_reported_as_success(self) -> None:
        result = self.run_task(FAIL_COMMAND="uv run --frozen zensical build --clean --strict")
        self.assertEqual(result.returncode, 17)
        self.assertNotIn("publish_ai_docs", self.log.read_text(encoding="utf-8"))

    def test_unknown_source_mode_is_rejected_before_installing_tools(self) -> None:
        result = self.run_task(BOXFERRY_WEBSITE_SOURCE_MODE="unknown")
        self.assertEqual(result.returncode, 2)
        self.assertFalse(self.log.exists())

    def test_unreadable_markdown_inventory_fails_before_a_reduced_result(self) -> None:
        result = self.run_task(
            FAIL_COMMAND="git ls-files --cached --others --exclude-standard -z -- *.md"
        )
        self.assertEqual(result.returncode, 17)
        self.assertNotIn("zensical", self.log.read_text(encoding="utf-8"))
