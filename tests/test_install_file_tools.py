"""Keep website installer selection thin and preserve shared failure outcomes."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

INSTALLER = Path(__file__).resolve().parents[1] / "scripts/install-file-tools.sh"


class FileToolInstallTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.script = self.root / "install-file-tools.sh"
        shutil.copy2(INSTALLER, self.script)
        self.arguments = self.root / "arguments.json"
        (self.root / "shared-ci.py").write_text(
            "import json, os, sys\nfrom pathlib import Path\n"
            'Path(os.environ["ARGUMENT_LOG"]).write_text(json.dumps(sys.argv[1:]))\n'
            'raise SystemExit(int(os.environ.get("INSTALL_STATUS", "0")))\n',
            encoding="utf-8",
        )

    def invoke(self, *arguments: str, status: int = 0) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            ["bash", str(self.script), *arguments],
            env={**os.environ, "ARGUMENT_LOG": str(self.arguments), "INSTALL_STATUS": str(status)},
            capture_output=True,
            check=False,
        )

    def test_complete_website_profile_is_delegated_with_literal_destination(self) -> None:
        destination = str(self.root / "installed tools")
        result = self.invoke(destination)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(
            json.loads(self.arguments.read_text()),
            ["tools", "--destination", destination, "--profile", "website"],
        )

    def test_maintenance_selects_only_lychee_and_preserves_failure_status(self) -> None:
        destination = str(self.root / "installed")
        result = self.invoke(destination, "--lychee-only", status=17)
        self.assertEqual(result.returncode, 17)
        self.assertEqual(
            json.loads(self.arguments.read_text()),
            ["tools", "--destination", destination, "--tools", "lychee"],
        )
        self.assertFalse(Path(destination).exists())

    def test_unknown_mode_and_extra_arguments_fail_before_bootstrap(self) -> None:
        for arguments in (("installed", "--unknown"), ("installed", "full", "extra")):
            with self.subTest(arguments=arguments):
                self.assertEqual(self.invoke(*arguments).returncode, 2)
                self.assertFalse(self.arguments.exists())
