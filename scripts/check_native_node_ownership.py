#!/usr/bin/env python3
"""Explicitly check native Node ownership using an existing verified Renovate cache."""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import json
import os
import subprocess
from collections.abc import Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def cached_runtime(runtime: Path | None, shared: Path) -> Path:
    """Refuse cold/foreign caches and verify through the selected canonical implementation."""
    if runtime is None or runtime.is_symlink() or not runtime.is_dir():
        raise RuntimeError("set BOXFERRY_RENOVATE_PACKAGE to an existing verified runtime cache")
    canonical = importlib.import_module("boxferry_ci.renovate_runtime")
    image, version = canonical._pin(shared / "automation/renovate-runtime.json")
    marker = runtime / "source-image.txt"
    if marker.is_symlink() or not marker.is_file() or marker.stat().st_size > 4096:
        raise RuntimeError("existing Renovate cache has no bounded source-image identity")
    if marker.read_text().strip() != image:
        raise RuntimeError("existing Renovate cache differs from the selected immutable image")

    def node_only(argv: Sequence[str], timeout: float) -> str:
        if not argv or argv[0] != "node":
            raise RuntimeError("native ownership verification forbids acquisition and engines")
        return subprocess.run(
            argv, check=True, capture_output=True, text=True, timeout=timeout
        ).stdout

    canonical._verify(runtime, version, node_only)
    return runtime.resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--report-json", type=Path, default=ROOT / "target/native-node-ownership.json"
    )
    options = parser.parse_args()
    try:
        selected = importlib.util.find_spec("boxferry_ci")
        if selected is None or selected.origin is None:
            raise RuntimeError("run through scripts/shared-ci.py run --task native-node-ownership")
        shared = Path(selected.origin).resolve().parents[3]
        setting = os.environ.get("BOXFERRY_RENOVATE_PACKAGE")
        runtime = cached_runtime(Path(setting) if setting else None, shared)
        result = subprocess.run(
            [
                "node",
                str(ROOT / "scripts/check-native-node-ownership.mjs"),
                str(runtime),
                str(ROOT),
                str(shared),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=90,
            cwd=ROOT,
        )
        report = json.loads(result.stdout)
        options.report_json.parent.mkdir(parents=True, exist_ok=True)
        options.report_json.write_text(json.dumps(report, indent=2) + "\n")
    except RuntimeError as error:
        raise SystemExit(f"Native Node ownership check failed: {error}") from None
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        raise SystemExit(
            f"Native Node ownership check failed ({type(error).__name__}); "
            "check the selected cache and native policy."
        ) from None
    print("Native Node ownership, remaining source pins and effective policy passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
