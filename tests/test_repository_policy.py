"""Repository-level tests for reproducibility and maintenance contracts."""

from __future__ import annotations

import json
import re
import subprocess
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACTION_PATTERN = re.compile(r"uses:\s+[^\s@]+@([0-9a-f]{40})\s+#\s+v?\d")
COLOR_PATTERN = re.compile(r"#[0-9a-fA-F]{3,8}\b|(?:rgb|hsl)a?\(")


class RepositoryPolicyTests(unittest.TestCase):
    """Keep local and hosted quality contracts aligned."""

    def test_zensical_uses_canonical_routes_and_dark_first_palette(self) -> None:
        with (ROOT / "zensical.toml").open("rb") as handle:
            project = tomllib.load(handle)["project"]

        self.assertEqual(project["site_url"], "https://boxferry.dev/")
        self.assertEqual(project["docs_dir"], ".generated/docs")
        self.assertEqual(project["site_dir"], "site")
        self.assertEqual(project["theme"]["palette"][0]["scheme"], "slate")
        self.assertEqual(project["theme"]["palette"][1]["scheme"], "default")

    def test_direct_python_tools_are_exactly_pinned(self) -> None:
        with (ROOT / "pyproject.toml").open("rb") as handle:
            configuration = tomllib.load(handle)

        dependencies = configuration["dependency-groups"]["dev"]
        self.assertEqual(
            dependencies,
            ["ruff==0.16.3", "zensical==0.0.56", "zizmor==1.28.0"],
        )
        self.assertEqual(configuration["tool"]["uv"]["required-version"], "==0.12.5")

    def test_every_github_action_is_immutable_and_versioned(self) -> None:
        workflows = sorted((ROOT / ".github" / "workflows").glob("*.yml"))
        self.assertTrue(workflows)
        for workflow in workflows:
            uses_lines = [
                line.strip()
                for line in workflow.read_text(encoding="utf-8").splitlines()
                if line.strip().startswith("uses:") or " uses:" in line
            ]
            for line in uses_lines:
                with self.subTest(workflow=workflow.name, line=line):
                    self.assertRegex(line, ACTION_PATTERN)

    def test_literal_colors_are_centralized(self) -> None:
        token_file = ROOT / "content" / "assets" / "stylesheets" / "tokens.css"
        candidates = [
            *ROOT.glob("content/**/*.css"),
            *ROOT.glob("content/**/*.html"),
            *ROOT.glob("content/**/*.svg"),
            *ROOT.glob("overrides/**/*.html"),
        ]
        for path in candidates:
            if path == token_file:
                continue
            with self.subTest(path=path.relative_to(ROOT)):
                self.assertIsNone(COLOR_PATTERN.search(path.read_text(encoding="utf-8")))

    def test_generated_and_temporary_paths_are_ignored(self) -> None:
        for path in (
            "temp/documentation-plan.md",
            ".generated/docs/index.md",
            "site/index.html",
            ".venv/bin/python",
            "node_modules/prettier/index.js",
        ):
            with self.subTest(path=path):
                result = subprocess.run(
                    ["git", "check-ignore", "--quiet", path],
                    cwd=ROOT,
                    check=False,
                )
                self.assertEqual(result.returncode, 0)

    def test_vscode_exposes_complete_check_build_and_preview(self) -> None:
        tasks = json.loads((ROOT / ".vscode" / "tasks.json").read_text(encoding="utf-8"))["tasks"]
        labels = {task["label"] for task in tasks}
        self.assertIn("BoxFerry Website: Format, lint, test, and build", labels)
        self.assertIn("BoxFerry Website: Build", labels)
        self.assertIn("BoxFerry Website: Preview", labels)

    def test_complete_gate_covers_every_repository_language(self) -> None:
        gate = (ROOT / "scripts" / "check-all.sh").read_text(encoding="utf-8")
        for expected in (
            "ruff format",
            "scripts/check-files.sh",
            "actionlint",
            "zizmor",
            "ruff check",
            "unittest discover",
            "assemble_docs.py",
            "zensical build",
            "verify_site.py",
            "lychee",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, gate)


if __name__ == "__main__":
    unittest.main()
