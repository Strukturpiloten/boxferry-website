#!/usr/bin/env python3
"""Select the small website maintenance check only for known, regular prose files.

CI executes this file from the trusted PR base revision. Unknown or unreadable
comparisons raise an error; the CI plan step converts that to the full gate.
"""

# cspell:ignore textconv

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

SHA = re.compile(r"[0-9a-f]{40}\Z")
MAX_DIFF_BYTES = 2_000_000
MAINTENANCE_PROSE = frozenset(
    {
        "README.md",
        "docs/architecture.md",
        "docs/content-guidelines.md",
        "docs/customization.md",
        "docs/decisions/README.md",
        "docs/dependency-policy.md",
        "docs/deployment.md",
    }
)


def git(root: Path, *arguments: str) -> bytes:
    result = subprocess.run(
        ["git", "-c", "diff.external=", *arguments],
        cwd=root,
        capture_output=True,
        check=False,
    )
    if result.returncode or len(result.stdout) > MAX_DIFF_BYTES:
        raise ValueError(f"Git comparison failed or exceeded {MAX_DIFF_BYTES} bytes")
    return result.stdout


def regular_markdown_blob(root: Path, revision: str, path: str) -> bool:
    entry = git(root, "ls-tree", "-z", revision, "--", path)
    return entry.startswith(b"100644 blob ") and entry.endswith(b"\t" + path.encode() + b"\0")


def classified_paths(raw: bytes) -> list[str] | None:
    """Only modified allowlisted paths qualify; additions and renames get full validation."""
    if not raw or len(raw) > MAX_DIFF_BYTES or not raw.endswith(b"\0"):
        return None
    fields = raw[:-1].split(b"\0")
    if len(fields) % 2:
        return None
    paths: list[str] = []
    for status, raw_path in zip(fields[::2], fields[1::2], strict=True):
        try:
            path = raw_path.decode("utf-8")
        except UnicodeDecodeError:
            return None
        if status != b"M" or path not in MAINTENANCE_PROSE or path in paths:
            return None
        paths.append(path)
    return paths or None


def profile(root: Path, base: str, tested: str | None) -> str:
    if not SHA.fullmatch(base) or (tested is not None and not SHA.fullmatch(tested)):
        return "full"
    try:
        if tested is None:
            # Local fast checks include tracked working-tree and staged edits.
            # Unknown untracked inputs cannot receive a reduced result.
            if git(root, "ls-files", "--others", "--exclude-standard", "-z"):
                return "full"
            raw = git(
                root, "diff", "--no-ext-diff", "--no-textconv", "--name-status", "-z", base, "--"
            )
            revision = "HEAD"
        else:
            if git(root, "rev-parse", "HEAD").strip() != tested.encode():
                return "full"
            raw = git(
                root,
                "diff",
                "--no-ext-diff",
                "--no-textconv",
                "--name-status",
                "-z",
                base,
                tested,
                "--",
            )
            revision = tested
        paths = classified_paths(raw)
        if paths is None:
            return "full"
        for path in paths:
            if not regular_markdown_blob(root, base, path):
                return "full"
            if tested is None:
                candidate = root / path
                if candidate.is_symlink() or not candidate.is_file():
                    return "full"
                # Index mode matters even when the working file is regular.
                if not git(root, "ls-files", "--stage", "-z", "--", path).startswith(b"100644 "):
                    return "full"
            elif not regular_markdown_blob(root, revision, path):
                return "full"
        return "maintenance"
    except (OSError, ValueError):
        return "full"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repository-root", type=Path, default=Path(__file__).resolve().parent.parent
    )
    parser.add_argument("--base")
    parser.add_argument("--tested")
    parser.add_argument("--list-docs", action="store_true")
    arguments = parser.parse_args()
    if arguments.list_docs:
        sys.stdout.buffer.write(
            b"\0".join(path.encode() for path in sorted(MAINTENANCE_PROSE)) + b"\0"
        )
        return
    if arguments.base is None:
        parser.error("--base is required unless --list-docs is used")
    print(profile(arguments.repository_root, arguments.base, arguments.tested))


if __name__ == "__main__":
    main()
