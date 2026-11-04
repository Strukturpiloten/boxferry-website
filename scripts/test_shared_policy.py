#!/usr/bin/env python3
"""Check website-specific expected results against its pinned shared implementation."""

from __future__ import annotations

import importlib
import importlib.util
import re
import tempfile
from pathlib import Path


def write_corrupt_download(_asset: object, path: Path) -> None:
    path.write_bytes(b"corrupt")


def validate(root: Path, automation: Path, configuration: Path | None = None) -> None:
    """Reuse canonical composition examples and classifier; add website expectations only."""
    examples = automation / "tests/test_presets.py"
    spec = importlib.util.spec_from_file_location("shared_preset_examples", examples)
    if spec is None or spec.loader is None:
        raise RuntimeError("the pinned shared implementation lacks consumer policy examples")
    presets = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(presets)
    composed = presets.consumer_config(configuration or root / ".github/renovate.json")
    presets.assert_automatic_policy(composed)
    historical = "deployment/historical-uv.json"
    for manager in composed["customManagers"]:
        for pattern in manager["managerFilePatterns"]:
            if not (pattern.startswith("/") and pattern.endswith("/")):
                raise AssertionError(
                    "review new manager patterns against historical integrity data"
                )
            if re.search(pattern[1:-1], historical):
                raise AssertionError("historical uv integrity became an automatic upgrade target")
    cases = (
        ("pep621", "pypi", "zensical", "pyproject.toml", "3 days"),
        ("npm", "npm", "prettier", "package.json", "3 days"),
        (
            "custom.regex",
            "git-refs",
            "Strukturpiloten/boxferry",
            "documentation-sources.toml",
            "0 days",
        ),
        (
            "custom.regex",
            "git-refs",
            "Strukturpiloten/unrelated",
            "documentation-sources.toml",
            "3 days",
        ),
        (
            "custom.regex",
            "git-refs",
            "Strukturpiloten/boxferry-impostor",
            "documentation-sources.toml",
            "3 days",
        ),
    )
    for manager, datasource, name, filename, age in cases:
        result = presets.effective(
            composed,
            {
                "manager": manager,
                "datasource": datasource,
                "packageName": name,
                "fileName": filename,
                "updateType": "major",
            },
        )
        if result["minimumReleaseAge"] != age:
            raise AssertionError(f"unexpected dependency age for {name}")
        if result["automerge"] is not True or result["dependencyDashboardApproval"] is not False:
            raise AssertionError(f"routine manual approval configured for {name}")

    tooling = importlib.import_module("boxferry_ci.tooling")
    if set(tooling.WEBSITE) != {"tombi", "shfmt", "shellcheck", "hadolint", "actionlint", "lychee"}:
        raise AssertionError("canonical website tool profile changed its required inventory")
    tooling.load_manifest()
    with tempfile.TemporaryDirectory() as directory:
        destination = Path(directory).resolve() / "tools"
        try:
            tooling.install(
                destination,
                ("lychee",),
                architecture="x86_64",
                downloader=write_corrupt_download,
            )
        except tooling.ToolError as error:
            if "SHA256" not in str(error):
                raise AssertionError(
                    "Lychee failed outside its expected integrity boundary"
                ) from error
        else:
            raise AssertionError("corrupt canonical Lychee bytes were accepted")
        if (destination / "lychee").exists():
            raise AssertionError("Lychee was installed before integrity validation")

    policy_module = importlib.import_module("boxferry_ci.policy")
    planner = importlib.import_module("boxferry_ci.planner")
    policy = policy_module.load_policy(root / "scripts/validation-policy.json")
    for path, expected in (
        ("README.md", {"prose"}),
        ("content/index.md", {"docs", "prose"}),
        ("content/docs/nested.md", {"docs", "prose"}),
        ("documentation-sources.toml", {"full"}),
        ("zensical.toml", {"full"}),
        ("scripts/check-site-docs.sh", {"full"}),
        ("scripts/validation-policy.json", {"full"}),
        ("uv.lock", {"full"}),
        ("unknown.txt", {"full"}),
    ):
        if (
            planner.path_profiles(
                path, (b"# Prose\n", b"# Revised prose\n"), policy, set(), complete_pair=True
            )
            != expected
        ):
            raise AssertionError(f"unexpected website validation profile for {path}")
    changed_code = (b"# Guide\n```sh\nold\n```\n", b"# Guide\n```sh\nnew\n```\n")
    if planner.path_profiles("README.md", changed_code, policy, set(), complete_pair=True) != {
        "full"
    }:
        raise AssertionError("private executable prose bypassed full validation")
    if planner.path_profiles("README.md", (b"# Prose\n",), policy, set()) != {"full"}:
        raise AssertionError("incomplete private Markdown pair received a reduced profile")
    if planner.path_profiles(
        "content/index.md", changed_code, policy, set(), complete_pair=True
    ) != {"docs", "executable-docs"}:
        raise AssertionError("public executable Markdown lost its semantic or site checks")
    if policy.selected_jobs(("docs", "prose")) != {"quality", "lockfile-release-age"}:
        raise AssertionError("mixed website prose omitted a required job")


def main() -> None:
    shared = importlib.util.find_spec("boxferry_ci")
    if shared is None or shared.origin is None:
        raise RuntimeError(
            "run this check through scripts/shared-ci.py run --task automation-policy"
        )
    validate(Path(__file__).resolve().parent.parent, Path(shared.origin).resolve().parents[2])
    print("Website shared validation and effective dependency-policy expectations passed.")


if __name__ == "__main__":
    main()
