"""Website file inventories and failures survive shared formatter dispatch."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class SharedFormatterTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        scripts = self.root / "scripts"
        scripts.mkdir()
        shutil.copyfile(ROOT / "scripts/check-files.sh", scripts / "check-files.sh")
        (scripts / "shared-ci.py").write_text(
            "import json, os, sys\n"
            "with open('calls.jsonl', 'a') as output:\n"
            "    output.write(json.dumps(sys.argv[1:]) + '\\n')\n"
            "sys.exit(17 if os.environ.get('FAIL_TOOL') in sys.argv[1:] else 0)\n",
            encoding="utf-8",
        )
        self.files = [
            "guide with spaces.md",
            "config.json",
            "config.yaml",
            "style.css",
            "page.html",
            "app.js",
            "test.mjs",
            "icon.svg",
        ]
        for name in self.files:
            (self.root / name).write_text("---\n" if name.endswith("yaml") else "fixture\n")
        tools = self.root / "bin"
        tools.mkdir()
        for tool in ("cspell", "hadolint", "shellcheck", "shfmt", "tombi"):
            path = tools / tool
            path.write_text("#!/bin/sh\nexit 0\n")
            path.chmod(0o755)
        git = tools / "git"
        git.write_text(
            "#!/bin/sh\nprintf '%s\\0' " + " ".join("'" + name + "'" for name in self.files) + "\n"
        )
        git.chmod(0o755)
        # Bare formatter executables must never win PATH discovery.
        for tool in ("prettier", "markdownlint-cli2"):
            path = tools / tool
            path.write_text("#!/bin/sh\nexit 99\n")
            path.chmod(0o755)
        self.environment = {**os.environ, "PATH": f"{tools}:{os.environ['PATH']}"}

    def run_files(self, mode: str, **environment: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(self.root / "scripts/check-files.sh"), mode],
            env={**self.environment, **environment},
            capture_output=True,
            text=True,
        )

    def test_check_and_fix_use_explicit_consumer_configuration_and_inventory(self) -> None:
        for mode in ("--check", "--fix"):
            with self.subTest(mode=mode):
                result = self.run_files(mode)
                self.assertEqual(result.returncode, 0, result.stderr)
                calls = [
                    json.loads(line)
                    for line in (self.root / "calls.jsonl").read_text().splitlines()
                ]
                self.assertTrue(any("--write" in call for call in calls) == (mode == "--fix"))
                for call in calls:
                    self.assertEqual(call[:3], ["node-tool", "--cwd", str(self.root)])
                    tool = call[3]
                    config = ".prettierrc.json" if tool == "prettier" else ".markdownlint.json"
                    self.assertEqual(call[call.index("--config") + 1], str(self.root / config))
                    if tool == "prettier":
                        self.assertIn(str(self.root / ".prettierignore"), call)
                for name in self.files:
                    self.assertTrue(any(name in call for call in calls), name)
                (self.root / "calls.jsonl").unlink()

    def test_each_formatter_failure_is_preserved(self) -> None:
        for tool in ("prettier", "markdownlint-cli2"):
            for mode in ("--check", "--fix"):
                with self.subTest(tool=tool, mode=mode):
                    self.assertEqual(self.run_files(mode, FAIL_TOOL=tool).returncode, 17)

    def test_missing_yaml_marker_still_fails(self) -> None:
        (self.root / "config.yaml").write_text("name: fixture\n")
        result = self.run_files("--check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Complete YAML documents must start with ---", result.stderr)
