"""Tests for local Hetzner server preparation."""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREPARATION_SCRIPT = ROOT / "scripts" / "prepare-hetzner-server.sh"


class HetznerServerPreparationTests(unittest.TestCase):
    """Exercise local validation without contacting an SSH server."""

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.temporary_path = Path(self.temporary_directory.name)
        self.binary_directory = self.temporary_path / "bin"
        self.binary_directory.mkdir()
        self.ssh_log = self.temporary_path / "ssh.log"
        self.scp_log = self.temporary_path / "scp.log"
        self.write_recorder("ssh", "BOXFERRY_TEST_SSH_LOG")
        self.write_recorder("scp", "BOXFERRY_TEST_SCP_LOG")

        self.environment = os.environ.copy()
        self.environment.update(
            {
                "PATH": f"{self.binary_directory}:{self.environment['PATH']}",
                "BOXFERRY_DEPLOY_HOST": "www734.your-server.de",
                "BOXFERRY_DEPLOY_PORT": "222",
                "BOXFERRY_DEPLOY_USER": "c3diiy",
                "BOXFERRY_DEPLOY_ROOT": "/usr/home/c3diiy/public_html/dev_boxferry",
                "BOXFERRY_TEST_SSH_LOG": str(self.ssh_log),
                "BOXFERRY_TEST_SCP_LOG": str(self.scp_log),
            }
        )

    def write_recorder(self, name: str, log_variable: str) -> None:
        recorder = self.binary_directory / name
        recorder.write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            f'for argument in "$@"; do printf "<%s>" "${{argument}}" '
            f'>> "${{{log_variable}}}"; done\n'
            f'printf "\\n" >> "${{{log_variable}}}"\n',
            encoding="utf-8",
        )
        recorder.chmod(0o700)

    def run_script(
        self,
        *,
        environment: dict[str, str] | None = None,
        arguments: tuple[str, ...] = (),
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(PREPARATION_SCRIPT), *arguments],
            cwd=self.temporary_path,
            env=environment or self.environment,
            check=False,
            capture_output=True,
            text=True,
        )

    def assert_no_remote_clients(self) -> None:
        self.assertFalse(self.ssh_log.exists())
        self.assertFalse(self.scp_log.exists())

    def test_prepares_layout_and_atomically_installs_updater(self) -> None:
        result = self.run_script()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("preparation completed", result.stdout)
        ssh_lines = self.ssh_log.read_text(encoding="utf-8").splitlines()
        scp_line = self.scp_log.read_text(encoding="utf-8")
        self.assertEqual(len(ssh_lines), 2)
        self.assertIn("<install -d -m 700", ssh_lines[0])
        self.assertIn("mv -f --", ssh_lines[1])
        self.assertIn("test ! -L", ssh_lines[1])
        self.assertIn("<c3diiy@www734.your-server.de>", ssh_lines[0])
        self.assertIn(str(ROOT / "deployment" / "hetzner" / "version-updater.sh"), scp_line)
        self.assertIn("version-updater.sh.upload", scp_line)

    def test_optional_administrator_identity_is_used_for_both_clients(self) -> None:
        identity = self.temporary_path / "administrator identity"
        identity.write_text("test identity\n", encoding="utf-8")
        environment = self.environment | {"BOXFERRY_ADMIN_SSH_IDENTITY_FILE": str(identity)}

        result = self.run_script(environment=environment)

        self.assertEqual(result.returncode, 0, result.stderr)
        for log in (self.ssh_log, self.scp_log):
            invocation = log.read_text(encoding="utf-8")
            self.assertIn(f"<-i><{identity}>", invocation)
            self.assertIn("<-o><IdentitiesOnly=yes>", invocation)

    def test_help_does_not_require_environment_values(self) -> None:
        result = self.run_script(environment=os.environ.copy(), arguments=("--help",))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("BOXFERRY_DEPLOY_ROOT", result.stdout)

    def test_every_required_value_is_enforced_before_ssh(self) -> None:
        for variable in (
            "BOXFERRY_DEPLOY_HOST",
            "BOXFERRY_DEPLOY_PORT",
            "BOXFERRY_DEPLOY_USER",
            "BOXFERRY_DEPLOY_ROOT",
        ):
            with self.subTest(variable=variable):
                environment = self.environment.copy()
                environment.pop(variable)
                result = self.run_script(environment=environment)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(variable, result.stderr)
                self.assert_no_remote_clients()

    def test_unsafe_connection_values_are_rejected_before_ssh(self) -> None:
        cases = (
            ("BOXFERRY_DEPLOY_HOST", "host;id"),
            ("BOXFERRY_DEPLOY_PORT", "0"),
            ("BOXFERRY_DEPLOY_PORT", "65536"),
            ("BOXFERRY_DEPLOY_PORT", "not-a-port"),
            ("BOXFERRY_DEPLOY_USER", "user name"),
            ("BOXFERRY_DEPLOY_USER", "-option"),
            ("BOXFERRY_DEPLOY_ROOT", "/"),
            ("BOXFERRY_DEPLOY_ROOT", "/safe/../escape"),
            ("BOXFERRY_DEPLOY_ROOT", "/safe/./root"),
            ("BOXFERRY_DEPLOY_ROOT", "/safe//root"),
            ("BOXFERRY_DEPLOY_ROOT", "/safe/root/"),
            ("BOXFERRY_DEPLOY_ROOT", "/path with spaces"),
        )
        for variable, value in cases:
            with self.subTest(variable=variable, value=value):
                environment = self.environment | {variable: value}
                result = self.run_script(environment=environment)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(variable, result.stderr)
                self.assert_no_remote_clients()

    def test_missing_administrator_identity_is_rejected_before_ssh(self) -> None:
        environment = self.environment | {
            "BOXFERRY_ADMIN_SSH_IDENTITY_FILE": str(self.temporary_path / "missing")
        }

        result = self.run_script(environment=environment)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("BOXFERRY_ADMIN_SSH_IDENTITY_FILE", result.stderr)
        self.assert_no_remote_clients()


if __name__ == "__main__":
    unittest.main()
