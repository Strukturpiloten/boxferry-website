"""Integration tests for the fixed-command Hetzner release updater."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UPDATER_SOURCE = ROOT / "deployment" / "hetzner" / "version-updater.sh"


class VersionUpdaterTests(unittest.TestCase):
    """Exercise activation, retention, rollback, and hostile requests."""

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.deployment_root = Path(self.temporary_directory.name) / "dev_boxferry"
        self.deploy_directory = self.deployment_root / ".deploy"
        self.incoming = self.deployment_root / "incoming"
        self.releases = self.deployment_root / "releases"
        self.deploy_directory.mkdir(parents=True)
        self.incoming.mkdir()
        self.releases.mkdir()
        self.updater = self.deploy_directory / "version-updater.sh"
        shutil.copyfile(UPDATER_SOURCE, self.updater)
        self.updater.chmod(0o700)

    def stage(self, revision: str, run_id: int = 1, attempt: int = 1) -> str:
        staging_name = f"{revision}-{run_id}-{attempt}"
        site = self.incoming / staging_name
        (site / "docs").mkdir(parents=True)
        (site / "assets" / "data").mkdir(parents=True)
        (site / ".boxferry-release").write_text(
            f"schema-version=1\nrevision={revision}\n",
            encoding="utf-8",
        )
        (site / ".htaccess").write_text("Options -Indexes\n", encoding="utf-8")
        (site / "index.html").write_text("<!doctype html>\n", encoding="utf-8")
        (site / "docs" / "index.html").write_text("<!doctype html>\n", encoding="utf-8")
        (site / "assets" / "data" / "deployment.json").write_text(
            json.dumps({"schema_version": 1, "website_revision": revision}, indent=2) + "\n",
            encoding="utf-8",
        )
        return staging_name

    def request(
        self, request: str, *, original_command: str = ""
    ) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["SSH_ORIGINAL_COMMAND"] = original_command
        return subprocess.run(
            [str(self.updater)],
            input=request + "\n",
            env=environment,
            check=False,
            capture_output=True,
            text=True,
        )

    def target(self, name: str) -> str | None:
        path = self.deployment_root / name
        return os.readlink(path) if path.is_symlink() else None

    def deploy(self, revision: str, run_id: int) -> None:
        staging_name = self.stage(revision, run_id)
        result = self.request(f"activate {revision} {staging_name}")
        self.assertEqual(result.returncode, 0, result.stderr)
        result = self.request(f"finalize {revision}")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_first_release_is_activated_and_finalized(self) -> None:
        revision = "1" * 40
        self.deploy(revision, 1)

        self.assertEqual(self.target("current"), f"releases/{revision}")
        self.assertIsNone(self.target("previous-1"))
        self.assertTrue((self.releases / revision).is_dir())
        self.assertFalse((self.deploy_directory / "pending-release").exists())

    def test_six_releases_retain_five_ordered_links_and_directories(self) -> None:
        revisions = [str(index) * 40 for index in range(1, 7)]
        for index, revision in enumerate(revisions, start=1):
            self.deploy(revision, index)

        self.assertEqual(self.target("current"), f"releases/{revisions[5]}")
        for index, name in enumerate(
            ("previous-1", "previous-2", "previous-3", "previous-4"),
            start=1,
        ):
            self.assertEqual(self.target(name), f"releases/{revisions[5 - index]}")
        self.assertEqual(
            sorted(path.name for path in self.releases.iterdir()),
            sorted(revisions[1:]),
        )

    def test_failed_release_can_restore_complete_link_state(self) -> None:
        first = "a" * 40
        second = "b" * 40
        self.deploy(first, 1)
        staging_name = self.stage(second, 2)

        activated = self.request(f"activate {second} {staging_name}")
        self.assertEqual(activated.returncode, 0, activated.stderr)
        rolled_back = self.request(f"rollback {second}")

        self.assertEqual(rolled_back.returncode, 0, rolled_back.stderr)
        self.assertEqual(self.target("current"), f"releases/{first}")
        self.assertIsNone(self.target("previous-1"))
        self.assertFalse((self.releases / second).exists())
        self.assertFalse((self.deploy_directory / "pending-release").exists())

    def test_redeploying_current_revision_is_idempotent(self) -> None:
        revision = "c" * 40
        self.deploy(revision, 1)
        staging_name = self.stage(revision, 2)

        activated = self.request(f"activate {revision} {staging_name}")
        finalized = self.request(f"finalize {revision}")

        self.assertEqual(activated.returncode, 0, activated.stderr)
        self.assertEqual(finalized.returncode, 0, finalized.stderr)
        self.assertFalse((self.incoming / staging_name).exists())
        self.assertEqual(self.target("current"), f"releases/{revision}")

    def test_finalized_retained_release_can_be_promoted(self) -> None:
        revisions = [character * 40 for character in ("1", "2", "3", "4", "5")]
        for index, revision in enumerate(revisions, start=1):
            self.deploy(revision, index)
        retained = revisions[2]

        promoted = self.request(f"promote {retained}")
        self.assertEqual(promoted.returncode, 0, promoted.stderr)
        finalized = self.request(f"finalize {retained}")

        self.assertEqual(finalized.returncode, 0, finalized.stderr)
        self.assertEqual(self.target("current"), f"releases/{retained}")
        self.assertEqual(self.target("previous-1"), f"releases/{revisions[4]}")
        self.assertEqual(self.target("previous-2"), f"releases/{revisions[3]}")
        self.assertEqual(self.target("previous-3"), f"releases/{revisions[1]}")
        self.assertEqual(self.target("previous-4"), f"releases/{revisions[0]}")
        self.assertEqual(len(list(self.releases.iterdir())), 5)

    def test_pending_retained_promotion_can_be_resumed(self) -> None:
        first = "7" * 40
        second = "8" * 40
        self.deploy(first, 1)
        self.deploy(second, 2)

        promoted = self.request(f"promote {first}")
        resumed = self.request(f"promote {first}")
        finalized = self.request(f"finalize {first}")

        self.assertEqual(promoted.returncode, 0, promoted.stderr)
        self.assertEqual(resumed.returncode, 0, resumed.stderr)
        self.assertIn("already promoted", resumed.stdout)
        self.assertEqual(finalized.returncode, 0, finalized.stderr)
        self.assertEqual(self.target("current"), f"releases/{first}")
        self.assertEqual(self.target("previous-1"), f"releases/{second}")

    def test_hostile_requests_and_original_commands_are_rejected(self) -> None:
        cases = (
            ("activate ../../etc/passwd unsafe", ""),
            ("finalize main", ""),
            ("delete " + "d" * 40, ""),
            ("finalize " + "d" * 40, "id"),
        )
        for request, original_command in cases:
            with self.subTest(request=request, original_command=original_command):
                result = self.request(request, original_command=original_command)
                self.assertNotEqual(result.returncode, 0)

    def test_symlink_inside_staging_release_is_rejected(self) -> None:
        revision = "e" * 40
        staging_name = self.stage(revision)
        (self.incoming / staging_name / "escape").symlink_to("/etc/passwd")

        result = self.request(f"activate {revision} {staging_name}")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("symbolic links", result.stderr)


if __name__ == "__main__":
    unittest.main()
