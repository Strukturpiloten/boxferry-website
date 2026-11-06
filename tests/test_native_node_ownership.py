"""Keep ordinary validation independent of native cache availability and acquisition."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from scripts import check_native_node_ownership as ownership
from scripts.check_native_node_ownership import ROOT, cached_runtime


class NativeNodeOwnershipTests(unittest.TestCase):
    def test_cold_cache_refuses_without_import_or_process(self) -> None:
        with (
            patch.object(ownership.importlib, "import_module") as canonical,
            patch.object(ownership.subprocess, "run") as process,
        ):
            with self.assertRaisesRegex(RuntimeError, "existing verified runtime cache"):
                cached_runtime(None, ROOT)
            canonical.assert_not_called()
            process.assert_not_called()

    def test_foreign_cache_refuses_before_verification(self) -> None:
        canonical = SimpleNamespace(_pin=Mock(return_value=("selected image", "selected version")))
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(
                ownership.importlib,
                "import_module",
                return_value=canonical,
            ),
            patch.object(ownership.subprocess, "run") as process,
        ):
            runtime = Path(directory)
            (runtime / "source-image.txt").write_text("unrelated image\n")
            with self.assertRaisesRegex(RuntimeError, "differs from the selected immutable image"):
                cached_runtime(runtime, ROOT)
            canonical._pin.assert_called_once_with(ROOT / "automation/renovate-runtime.json")
            process.assert_not_called()

    def test_canonical_verification_can_only_execute_node(self) -> None:
        def attempted_acquisition(_runtime: Path, _version: str, command: object) -> None:
            assert callable(command)
            command(["podman", "pull", "must-not-run"], 30)

        canonical = SimpleNamespace(
            _pin=Mock(return_value=("selected image", "selected version")),
            _verify=attempted_acquisition,
        )
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(
                ownership.importlib,
                "import_module",
                return_value=canonical,
            ),
            patch.object(ownership.subprocess, "run") as process,
        ):
            runtime = Path(directory)
            (runtime / "source-image.txt").write_text("selected image\n")
            with self.assertRaisesRegex(RuntimeError, "forbids acquisition and engines"):
                cached_runtime(runtime, ROOT)
            process.assert_not_called()

    def test_existing_cache_uses_selected_canonical_verifier(self) -> None:
        def verify_node(runtime: Path, version: str, command: object) -> None:
            assert callable(command)
            self.assertEqual(version, "selected version")
            self.assertEqual(command(["node", "--version"], 30), "native proof")
            self.assertTrue(runtime.is_dir())

        canonical = SimpleNamespace(
            _pin=Mock(return_value=("selected image", "selected version")), _verify=verify_node
        )
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(
                ownership.importlib,
                "import_module",
                return_value=canonical,
            ),
            patch.object(
                ownership.subprocess,
                "run",
                return_value=SimpleNamespace(stdout="native proof"),
            ) as process,
        ):
            runtime = Path(directory)
            (runtime / "source-image.txt").write_text("selected image\n")
            self.assertEqual(cached_runtime(runtime, ROOT), runtime.resolve())
            process.assert_called_once_with(
                ["node", "--version"], check=True, capture_output=True, text=True, timeout=30
            )

    def test_native_task_is_explicit_and_normal_quality_has_no_runtime_requirement(self) -> None:
        policy = json.loads((ROOT / "scripts/validation-policy.json").read_text())
        tasks = policy["tasks"]
        self.assertEqual(
            tasks["native-node-ownership"]["commands"],
            [["python", "scripts/check_native_node_ownership.py"]],
        )
        for task in ("python-quality", "python-format", "python-format-check", "automation-policy"):
            self.assertNotIn("native_node_ownership", json.dumps(tasks[task]))


if __name__ == "__main__":
    unittest.main()
