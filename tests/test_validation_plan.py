"""Consumer contract for shared validation policy and the thin local launcher."""

from __future__ import annotations

import importlib.util
import io
import json
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("shared_bootstrap", ROOT / "scripts/shared-ci.py")
assert SPEC is not None and SPEC.loader is not None
bootstrap = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bootstrap)


class ValidationPolicyTests(unittest.TestCase):
    def test_profiles_keep_complete_site_and_narrow_prose_tasks_distinct(self) -> None:
        policy = json.loads((ROOT / "scripts/validation-policy.json").read_text())
        self.assertEqual(policy["repository"], "Strukturpiloten/boxferry-website")
        self.assertEqual(policy["jobs"], ["quality", "lockfile-release-age"])
        self.assertEqual(
            policy["local_commands"]["full"], [["bash", "scripts/check-all.sh", "--check"]]
        )
        self.assertEqual(policy["local_commands"]["docs"], [["bash", "scripts/check-site-docs.sh"]])
        self.assertEqual(
            policy["local_commands"]["prose"], [["bash", "scripts/check-maintenance-docs.sh"]]
        )
        self.assertEqual(
            policy["local_commands"]["executable-docs"], policy["local_commands"]["prose"]
        )
        self.assertEqual(set(policy["path_profiles"]), {"prose", "docs"})
        self.assertIn("content/*.md", policy["path_profiles"]["docs"])
        self.assertIn("content/**/*.md", policy["path_profiles"]["docs"])
        for paths in policy["path_profiles"].values():
            for forbidden in (
                "scripts/**",
                "documentation-sources.toml",
                "zensical.toml",
                "**/*.py",
            ):
                self.assertNotIn(forbidden, paths)

    def test_canonical_tool_tasks_use_shared_executables_without_local_versions(self) -> None:
        policy = json.loads((ROOT / "scripts/validation-policy.json").read_text())
        self.assertEqual(
            policy["tasks"]["python-quality"]["commands"],
            [["ruff", "check", "scripts", "tests"], ["ty", "check"]],
        )
        for name in ("complete-fix", "complete-check", "site-docs", "maintenance"):
            command = policy["tasks"][name]["commands"][0]
            self.assertEqual(command[:2], ["env", "BOXFERRY_WEBSITE_SHARED_TOOLS=1"])

    def test_local_launcher_delegates_without_a_local_classifier(self) -> None:
        script = (ROOT / "scripts/check-changes.sh").read_text()
        self.assertIn('shared-ci.py" run-local --base-ref', script)
        self.assertFalse((ROOT / "scripts/validation-plan.py").exists())


class FrontloaderDelegationTests(unittest.TestCase):
    def test_interface_one_passes_raw_argv_to_the_manifest_selected_bootstrap(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "automation"
            capture = Path(directory) / "arguments.json"
            implementation = project / "src/boxferry_ci/bootstrap.py"
            implementation.parent.mkdir(parents=True)
            implementation.write_text(
                "import json\nfrom pathlib import Path\n"
                "def run_project(repository_root, project, arguments):\n"
                f"    Path({str(capture)!r}).write_text(json.dumps(arguments))\n"
                "    return 17\n",
                encoding="utf-8",
            )
            revision = "a" * 40
            for arguments in (
                ["plan", "--config", "/trusted/base.json", "--repository-root", "/tested/source"],
                ["run-local", "--base-ref", "origin/main"],
                ["tools", "--destination", "target/tools", "--profile", "website"],
            ):
                with (
                    self.subTest(arguments=arguments),
                    patch.object(
                        bootstrap,
                        "load_config",
                        return_value={
                            "revision": revision,
                            "policy": "scripts/validation-policy.json",
                        },
                    ),
                    patch.object(
                        bootstrap, "prepare_implementation", return_value=project
                    ) as prepare,
                    patch("sys.stderr", new_callable=io.StringIO),
                ):
                    self.assertEqual(bootstrap.main(arguments), 17)
                    prepare.assert_called_once_with(ROOT, revision)
                    self.assertEqual(json.loads(capture.read_text()), arguments)
            self.assertEqual(bootstrap.INTERFACE, 1)

    def test_incompatible_selected_implementation_fails_before_cli_execution(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "automation"
            implementation = project / "src/boxferry_ci/bootstrap.py"
            implementation.parent.mkdir(parents=True)
            implementation.write_text(
                "# Missing required interface entry point.\n", encoding="utf-8"
            )
            with (
                patch.object(
                    bootstrap,
                    "load_config",
                    return_value={"revision": "b" * 40, "policy": "scripts/validation-policy.json"},
                ),
                patch.object(bootstrap, "prepare_implementation", return_value=project),
                patch("sys.stderr", new_callable=io.StringIO) as errors,
            ):
                self.assertEqual(bootstrap.main(["plan"]), 2)
                self.assertIn("interface-1 run_project", errors.getvalue())

    def test_loader_archives_only_exact_inert_cargo_metadata(self) -> None:
        with tempfile.TemporaryDirectory(prefix="website-loader-archive-") as directory:
            root = Path(directory)
            marker = root / "must-not-execute"
            payload = f"FROM scratch\nRUN touch {marker}\n".encode()
            archive_path = root / "metadata.tar"

            def write_archive(name: str, kind: bytes = tarfile.REGTYPE) -> None:
                with tarfile.open(archive_path, "w") as archive:
                    member = tarfile.TarInfo(name)
                    member.type = kind
                    member.size = len(payload) if kind == tarfile.REGTYPE else 0
                    member.linkname = "outside" if kind == tarfile.SYMTYPE else ""
                    archive.addfile(member, io.BytesIO(payload) if member.size else None)

            write_archive(".devcontainer/Dockerfile")
            output = root / "valid"
            output.mkdir()
            bootstrap.extract_archive(archive_path, output)
            self.assertEqual((output / ".devcontainer/Dockerfile").read_bytes(), payload)
            self.assertFalse(marker.exists())
            for index, (name, kind) in enumerate(
                (
                    (".devcontainer/payload.sh", tarfile.REGTYPE),
                    (".devcontainer/Dockerfile/extra", tarfile.REGTYPE),
                    (".devcontainer/Dockerfile", tarfile.SYMTYPE),
                    (".devcontainer", tarfile.REGTYPE),
                )
            ):
                with (
                    self.subTest(name=name, kind=kind),
                    self.assertRaises(bootstrap.BootstrapError),
                ):
                    write_archive(name, kind)
                    rejected = root / f"rejected-{index}"
                    rejected.mkdir()
                    bootstrap.extract_archive(archive_path, rejected)
