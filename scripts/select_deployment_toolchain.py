#!/usr/bin/env python3
"""Select tooling from inert metadata in an already approved main-history checkout."""

from __future__ import annotations

import argparse
import json
import platform
import re
import subprocess
import tomllib
from pathlib import Path

SHA = re.compile(r"[0-9a-f]{40}\Z")
DIGEST = re.compile(r"[0-9a-f]{64}\Z")
LEGACY_UV = "0.13.5"
MAX_METADATA_BYTES = 65_536


def read_metadata(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_METADATA_BYTES:
        raise ValueError("toolchain metadata must be a bounded regular file")
    content = path.read_bytes()
    if len(content) > MAX_METADATA_BYTES:
        raise ValueError("toolchain metadata exceeds its size budget")
    return content


def unique_fields(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("toolchain metadata repeats a field")
        result[key] = value
    return result


def select_toolchain(
    source: Path, historical: Path, *, system: str, architecture: str
) -> dict[str, str]:
    """No selected-source executable is imported or invoked to discover its versions."""
    manifest = source / ".github/automation.json"
    if manifest.exists() or manifest.is_symlink():
        data = json.loads(read_metadata(manifest), object_pairs_hook=unique_fields)
        if (
            not isinstance(data, dict)
            or set(data) != {"schema", "repository", "revision", "policy", "interface"}
            or type(data["schema"]) is not int
            or data["schema"] != 1
            or type(data["interface"]) is not int
            or data["interface"] != 1
            or data["repository"] != "Strukturpiloten/boxferry"
            or not isinstance(data["revision"], str)
            or SHA.fullmatch(data["revision"]) is None
            or data["policy"] != "scripts/validation-policy.json"
        ):
            raise ValueError("unsupported selected-source automation manifest")
        return {"mode": "canonical", "automation_sha": data["revision"]}

    project = tomllib.loads(read_metadata(source / "pyproject.toml").decode("utf-8"))
    tools = project.get("tool", {})
    uv = tools.get("uv", {}) if isinstance(tools, dict) else None
    requirement = uv.get("required-version") if isinstance(uv, dict) else None
    if requirement != f"=={LEGACY_UV}":
        raise ValueError(
            "pre-adoption rebuild supports only the historical exact uv 0.13.5 constraint"
        )
    record = json.loads(read_metadata(historical), object_pairs_hook=unique_fields)
    if (
        not isinstance(record, dict)
        or type(record.get("schema")) is not int
        or record.get("schema") != 1
        or record.get("version") != LEGACY_UV
    ):
        raise ValueError("invalid historical uv integrity record")
    if system != "Linux" or architecture != "x86_64":
        raise ValueError(
            "historical deployment tooling supports only the reviewed Linux x86_64 runner"
        )
    assets = record.get("assets", {})
    asset = assets.get("Linux-x86_64", {}) if isinstance(assets, dict) else None
    if not isinstance(asset, dict):
        raise ValueError("invalid historical uv asset record")
    digest = asset.get("sha256")
    url = f"https://github.com/astral-sh/uv/releases/download/{LEGACY_UV}/uv-x86_64-unknown-linux-gnu.tar.gz"
    if not isinstance(digest, str) or DIGEST.fullmatch(digest) is None or asset.get("url") != url:
        raise ValueError("historical uv archive lacks reviewed integrity")
    return {"mode": "legacy", "legacy_version": LEGACY_UV, "legacy_checksum": digest}


def verify_checkout(source: Path, revision: str) -> None:
    if SHA.fullmatch(revision) is None:
        raise ValueError("selected source revision must be an exact lowercase commit SHA")
    result = subprocess.run(
        [
            "git",
            "-c",
            "core.fsmonitor=false",
            "-c",
            "core.hooksPath=/dev/null",
            "rev-parse",
            "HEAD",
        ],
        cwd=source,
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    if result.stdout.strip() != revision:
        raise ValueError("selected source checkout does not match the approved request revision")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--historical-record", type=Path, required=True)
    parser.add_argument("--github-output", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()
    try:
        verify_checkout(args.source_root, args.source_revision)
        selected = select_toolchain(
            args.source_root,
            args.historical_record,
            system=platform.system(),
            architecture=platform.machine(),
        )
        with args.github_output.open("a", encoding="utf-8") as stream:
            for key, value in selected.items():
                stream.write(f"{key}={value}\n")
        with args.summary.open("a", encoding="utf-8") as stream:
            stream.write(
                f"Deployment build source: `{args.source_revision}`; "
                f"tooling: `{selected['mode']}`.\n"
            )
            if selected["mode"] == "legacy":
                stream.write(
                    "Historical uv 0.13.5; selected-source Python metadata remains authoritative.\n"
                )
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        print(
            "Deployment toolchain selection failed. "
            "Check approved source identity and metadata: require an interface-1 manifest, "
            "or exact historical uv 0.13.5 with reviewed integrity on the supported runner. "
            "Retained-artifact rollback does not require a rebuild."
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
