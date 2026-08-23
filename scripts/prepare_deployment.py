#!/usr/bin/env python3
"""Add deterministic Apache and release metadata to a built static site."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APACHE_POLICY = ROOT / "deployment" / "apache" / ".htaccess"
DEPLOYMENT_METADATA = Path("assets/data/deployment.json")
RELEASE_MANIFEST = Path(".boxferry-release")
REVISION_PATTERN = re.compile(r"[0-9a-f]{40}")


class DeploymentPreparationError(RuntimeError):
    """Describe an unsafe or incomplete deployment artifact."""


def resolve_revision(repository_root: Path, revision: str | None) -> str:
    """Return a validated exact website revision."""
    if revision is None:
        try:
            revision = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=repository_root,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
        except (OSError, subprocess.CalledProcessError) as error:
            raise DeploymentPreparationError("cannot resolve the website Git revision") from error
    if not REVISION_PATTERN.fullmatch(revision):
        raise DeploymentPreparationError("website revision must be exactly 40 lowercase hex digits")
    return revision


def prepare_deployment(
    site_directory: Path,
    *,
    revision: str | None = None,
    repository_root: Path = ROOT,
) -> str:
    """Install server policy and revision evidence into an existing site tree."""
    site = site_directory.resolve()
    if not site.is_dir():
        raise DeploymentPreparationError(f"site directory does not exist: {site_directory}")

    exact_revision = resolve_revision(repository_root, revision)
    apache_policy = repository_root / APACHE_POLICY.relative_to(ROOT)
    if not apache_policy.is_file():
        raise DeploymentPreparationError(f"Apache policy does not exist: {apache_policy}")

    shutil.copyfile(apache_policy, site / ".htaccess")
    (site / RELEASE_MANIFEST).write_text(
        f"schema-version=1\nrevision={exact_revision}\n",
        encoding="utf-8",
    )
    metadata_path = site / DEPLOYMENT_METADATA
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "website_revision": exact_revision,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return exact_revision


def main() -> int:
    """Prepare a static site for immutable deployment."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("site_directory", nargs="?", type=Path, default=Path("site"))
    parser.add_argument("--revision")
    arguments = parser.parse_args()
    try:
        revision = prepare_deployment(arguments.site_directory, revision=arguments.revision)
    except DeploymentPreparationError as error:
        print(f"boxferry-website: deployment preparation failed: {error}", file=sys.stderr)
        return 1
    print(f"Prepared BoxFerry static release {revision}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
