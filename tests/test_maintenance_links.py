"""The maintenance lane rejects broken relative links without building the site."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which("lychee"), "the pinned Lychee executable is unavailable")
class MaintenanceLinkTests(unittest.TestCase):
    def test_broken_local_link_fails_the_maintenance_command(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository = Path(temporary)
            scripts = repository / "scripts"
            scripts.mkdir()
            for filename in ("check-maintenance-docs.sh", "validation-plan.py"):
                shutil.copyfile(ROOT / "scripts" / filename, scripts / filename)
            shutil.copyfile(ROOT / "lychee.toml", repository / "lychee.toml")

            listed = subprocess.check_output(
                ["python3", str(scripts / "validation-plan.py"), "--list-docs"]
            )
            for raw_name in listed.rstrip(b"\0").split(b"\0"):
                path = repository / raw_name.decode()
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("# Maintenance document\n", encoding="utf-8")

            tools = repository / "stub-tools"
            tools.mkdir()
            for name in ("npm", "prettier", "markdownlint-cli2", "cspell", "git"):
                helper = tools / name
                helper.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
                helper.chmod(0o755)
            environment = os.environ.copy()
            environment["PATH"] = f"{tools}:{environment['PATH']}"
            command = ["bash", str(scripts / "check-maintenance-docs.sh")]

            (repository / "README.md").write_text(
                "# Maintenance document\n\n[Architecture](docs/architecture.md)\n",
                encoding="utf-8",
            )
            healthy = subprocess.run(command, cwd=repository, env=environment, capture_output=True)
            self.assertEqual(healthy.returncode, 0, healthy.stderr.decode(errors="replace"))

            (repository / "README.md").write_text(
                "# Maintenance document\n\n[Missing](docs/does-not-exist.md)\n",
                encoding="utf-8",
            )
            broken = subprocess.run(command, cwd=repository, env=environment, capture_output=True)
            self.assertNotEqual(broken.returncode, 0)
            self.assertIn(b"does-not-exist.md", broken.stdout + broken.stderr)


if __name__ == "__main__":
    unittest.main()
