#!/usr/bin/env python3
"""Build first-party Rust API documentation from assembled source revisions."""

from __future__ import annotations

import argparse
import html
import os
import shutil
import subprocess
import sys
from pathlib import Path

if __package__:
    from scripts.assemble_docs import AssemblyError, Manifest, RepositorySource, load_manifest
else:
    from assemble_docs import AssemblyError, Manifest, RepositorySource, load_manifest


def _git_revision(repository: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repository,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise AssemblyError(f"cannot inspect Rustdoc source repository: {repository}") from error
    return result.stdout.strip()


def _source_root(manifest: Manifest, repository: RepositorySource, source_mode: str) -> Path:
    if source_mode == "local":
        source = next(
            (
                candidate
                for candidate in repository.local_directories
                if candidate.is_dir() and (candidate / ".git").exists()
            ),
            None,
        )
        if source is None:
            raise AssemblyError(f"local Rustdoc source repository is missing: {repository.name}")
        return source

    source = manifest.root / ".generated" / "sources" / repository.name
    if not source.is_dir() or not (source / ".git").exists():
        raise AssemblyError(
            f"locked Rustdoc source is missing for {repository.name}; assemble documentation first"
        )
    if _git_revision(source) != repository.revision:
        raise AssemblyError(f"locked Rustdoc source revision mismatch for {repository.name}")
    return source


def _write_redirect(destination: Path, crate: str) -> None:
    escaped_crate = html.escape(crate, quote=True)
    destination.joinpath("index.html").write_text(
        "\n".join(
            (
                "<!doctype html>",
                '<html lang="en">',
                "<head>",
                '  <meta charset="utf-8">',
                f'  <meta http-equiv="refresh" content="0; url={escaped_crate}/">',
                f"  <title>{escaped_crate} Rust API</title>",
                f'  <link rel="canonical" href="{escaped_crate}/">',
                "</head>",
                f'<body><a href="{escaped_crate}/">Open the {escaped_crate} Rust API</a></body>',
                "</html>",
                "",
            )
        ),
        encoding="utf-8",
        newline="\n",
    )


def build_rustdoc(manifest: Manifest, source_mode: str, site_directory: Path) -> None:
    """Build every declared Rustdoc target into an existing static site."""
    if source_mode not in {"local", "locked"}:
        raise AssemblyError("source mode must be local or locked")
    site = site_directory.resolve()
    if not site.is_dir() or not site.is_relative_to(manifest.root):
        raise AssemblyError("site directory must be an existing directory inside the repository")

    targets_root = manifest.root / ".generated" / "rustdoc-targets"
    for repository in manifest.repositories:
        rustdoc = repository.rustdoc
        if rustdoc is None:
            continue
        source = _source_root(manifest, repository, source_mode)
        target = targets_root / repository.name
        if target.exists():
            shutil.rmtree(target)
        environment = os.environ.copy()
        environment["RUSTDOCFLAGS"] = "-D warnings"
        try:
            subprocess.run(
                [
                    "cargo",
                    "doc",
                    "--locked",
                    "--no-deps",
                    "--package",
                    rustdoc.package,
                    "--target-dir",
                    str(target),
                ],
                cwd=source,
                env=environment,
                check=True,
            )
        except (OSError, subprocess.CalledProcessError) as error:
            raise AssemblyError(f"Rustdoc build failed for {repository.name}") from error

        generated = target / "doc"
        crate_index = generated / rustdoc.crate / "index.html"
        if not crate_index.is_file():
            raise AssemblyError(
                "Rustdoc did not generate the declared crate "
                f"`{rustdoc.crate}` for {repository.name}"
            )
        destination = site.joinpath(*rustdoc.destination.parts)
        if destination.exists() or destination.is_symlink():
            raise AssemblyError(f"Rustdoc destination already exists: {rustdoc.destination}")
        shutil.copytree(generated, destination, symlinks=False)
        _write_redirect(destination, rustdoc.crate)


def main() -> int:
    """Run the first-party Rustdoc builder."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("documentation-sources.toml"))
    parser.add_argument("--source-mode", choices=("local", "locked"), default="local")
    parser.add_argument("--site-directory", type=Path, default=Path("site"))
    arguments = parser.parse_args()
    try:
        manifest = load_manifest(arguments.manifest)
        build_rustdoc(manifest, arguments.source_mode, arguments.site_directory)
    except AssemblyError as error:
        print(f"boxferry-website: Rustdoc build failed: {error}", file=sys.stderr)
        return 1
    print("BoxFerry first-party Rust API documentation built successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
