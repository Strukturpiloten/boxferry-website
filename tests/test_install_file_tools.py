"""Integrity failures stop the bounded Lychee installer before publication."""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

INSTALLER = Path(__file__).resolve().parents[1] / "scripts" / "install-file-tools.sh"


class FileToolInstallTests(unittest.TestCase):
    def test_corrupt_lychee_archive_is_rejected_before_install(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fake_bin = root / "fake-bin"
            fake_bin.mkdir()
            fake_curl = fake_bin / "curl"
            fake_curl.write_text(
                "#!/bin/sh\n"
                'while [ "$#" -gt 0 ]; do\n'
                '  if [ "$1" = --output ]; then shift; printf corrupt > "$1"; exit 0; fi\n'
                "  shift\n"
                "done\n"
                "exit 1\n",
                encoding="utf-8",
            )
            fake_curl.chmod(0o755)
            environment = os.environ.copy()
            environment["PATH"] = f"{fake_bin}:{environment['PATH']}"
            destination = root / "installed"
            result = subprocess.run(
                ["bash", str(INSTALLER), str(destination), "--lychee-only"],
                env=environment,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((destination / "lychee").exists())

    def test_unknown_mode_is_rejected_before_download(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "installed"
            result = subprocess.run(
                ["bash", str(INSTALLER), str(destination), "--unknown"],
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertFalse(destination.exists())


if __name__ == "__main__":
    unittest.main()
