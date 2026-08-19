#!/usr/bin/env python3
"""Assemble website-owned and repository-owned documentation safely."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

SCHEMA_VERSION = 1
REVISION_PATTERN = re.compile(r"[0-9a-f]{40}")
REPOSITORY_NAME_PATTERN = re.compile(r"[a-z0-9][a-z0-9-]*")
GITHUB_PREFIX = "https://github.com/Strukturpiloten/"


class AssemblyError(RuntimeError):
    """Describe an invalid manifest or unsafe source tree."""


@dataclass(frozen=True)
class DocumentMapping:
    """Map one repository path into one public documentation path."""

    source: PurePosixPath
    destination: PurePosixPath


@dataclass(frozen=True)
class RepositorySource:
    """Describe one exact external documentation source."""

    name: str
    repository: str
    revision: str
    local_directories: tuple[Path, ...]
    documents: tuple[DocumentMapping, ...]


@dataclass(frozen=True)
class Manifest:
    """Validated documentation assembly configuration."""

    root: Path
    content_directory: Path
    staging_directory: Path
    repositories: tuple[RepositorySource, ...]


def _required_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AssemblyError(f"{label} must be a TOML table")
    return value


def _required_string(table: dict[str, Any], key: str, label: str) -> str:
    value = table.get(key)
    if not isinstance(value, str) or not value.strip():
        raise AssemblyError(f"{label}.{key} must be a non-empty string")
    if "\x00" in value:
        raise AssemblyError(f"{label}.{key} must not contain a NUL byte")
    return value


def _required_string_list(table: dict[str, Any], key: str, label: str) -> tuple[str, ...]:
    value = table.get(key)
    if not isinstance(value, list) or not value:
        raise AssemblyError(f"{label}.{key} must be a non-empty array of strings")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip() or "\x00" in item:
            raise AssemblyError(f"{label}.{key} must contain only non-empty strings")
        result.append(item)
    return tuple(result)


def _safe_relative_path(value: str, label: str) -> PurePosixPath:
    if "\\" in value:
        raise AssemblyError(f"{label} must use forward slashes")
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise AssemblyError(f"{label} must be a normalized relative path")
    return path


def _safe_owned_directory(root: Path, value: str, label: str) -> Path:
    relative = _safe_relative_path(value, label)
    resolved = (root / Path(*relative.parts)).resolve()
    if not resolved.is_relative_to(root):
        raise AssemblyError(f"{label} must stay inside the website repository")
    if resolved == root:
        raise AssemblyError(f"{label} must not resolve to the repository root")
    return resolved


def load_manifest(path: Path) -> Manifest:
    """Load and validate a source manifest without touching its source repositories."""
    manifest_path = path.resolve()
    root = manifest_path.parent
    try:
        with manifest_path.open("rb") as handle:
            data = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise AssemblyError(f"cannot read documentation source manifest: {error}") from error

    if data.get("schema-version") != SCHEMA_VERSION:
        raise AssemblyError(f"schema-version must be {SCHEMA_VERSION}")

    site = _required_mapping(data.get("site"), "site")
    content_directory = _safe_owned_directory(
        root,
        _required_string(site, "content-directory", "site"),
        "site.content-directory",
    )
    staging_directory = _safe_owned_directory(
        root,
        _required_string(site, "staging-directory", "site"),
        "site.staging-directory",
    )
    if content_directory == staging_directory:
        raise AssemblyError("content and staging directories must differ")

    raw_repositories = data.get("repositories")
    if not isinstance(raw_repositories, list) or not raw_repositories:
        raise AssemblyError("repositories must contain at least one source table")

    names: set[str] = set()
    destinations: set[PurePosixPath] = set()
    repositories: list[RepositorySource] = []
    for index, raw_repository in enumerate(raw_repositories, start=1):
        label = f"repositories[{index}]"
        table = _required_mapping(raw_repository, label)
        name = _required_string(table, "name", label)
        if not REPOSITORY_NAME_PATTERN.fullmatch(name):
            raise AssemblyError(f"{label}.name must use lowercase letters, digits, and hyphens")
        if name in names:
            raise AssemblyError(f"duplicate repository name: {name}")
        names.add(name)

        repository = _required_string(table, "repository", label)
        if not repository.startswith(GITHUB_PREFIX) or not repository.endswith(".git"):
            raise AssemblyError(f"{label}.repository must be an HTTPS Strukturpiloten Git URL")

        revision = _required_string(table, "revision", label)
        if not REVISION_PATTERN.fullmatch(revision):
            raise AssemblyError(f"{label}.revision must be a lowercase 40-character Git SHA")

        local_directory_values = _required_string_list(table, "local-directories", label)
        local_directories = tuple((root / value).resolve() for value in local_directory_values)

        raw_documents = table.get("documents", [])
        if not isinstance(raw_documents, list):
            raise AssemblyError(f"{label}.documents must be an array of tables")
        documents: list[DocumentMapping] = []
        for document_index, raw_document in enumerate(raw_documents, start=1):
            document_label = f"{label}.documents[{document_index}]"
            document = _required_mapping(raw_document, document_label)
            source = _safe_relative_path(
                _required_string(document, "source", document_label),
                f"{document_label}.source",
            )
            destination = _safe_relative_path(
                _required_string(document, "destination", document_label),
                f"{document_label}.destination",
            )
            if destination in destinations:
                raise AssemblyError(f"duplicate documentation destination: {destination}")
            destinations.add(destination)
            documents.append(DocumentMapping(source=source, destination=destination))

        repositories.append(
            RepositorySource(
                name=name,
                repository=repository,
                revision=revision,
                local_directories=local_directories,
                documents=tuple(documents),
            )
        )

    return Manifest(
        root=root,
        content_directory=content_directory,
        staging_directory=staging_directory,
        repositories=tuple(repositories),
    )


def _copy_tree(source: Path, destination: Path) -> None:
    if source.is_symlink():
        raise AssemblyError(f"symbolic links are not accepted: {source}")
    if not source.exists():
        raise AssemblyError(f"documentation source does not exist: {source}")

    if source.is_file():
        if destination.exists():
            raise AssemblyError(f"documentation destination already exists: {destination}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        return

    if not source.is_dir():
        raise AssemblyError(f"documentation source is not a regular file or directory: {source}")
    if destination.exists():
        raise AssemblyError(f"documentation destination already exists: {destination}")
    destination.mkdir(parents=True)
    for entry in sorted(source.rglob("*")):
        if entry.is_symlink():
            raise AssemblyError(f"symbolic links are not accepted: {entry}")
        relative = entry.relative_to(source)
        target = destination / relative
        if entry.is_dir():
            target.mkdir(exist_ok=True)
        elif entry.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(entry, target)
        else:
            raise AssemblyError(f"unsupported documentation source entry: {entry}")


def _run_git(arguments: list[str], *, cwd: Path | None = None) -> str:
    try:
        result = subprocess.run(
            ["git", *arguments],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise AssemblyError(f"Git source acquisition failed: {' '.join(arguments[:2])}") from error
    return result.stdout.strip()


def _locked_checkout(manifest: Manifest, repository: RepositorySource) -> Path:
    sources_root = manifest.root / ".generated" / "sources"
    checkout = sources_root / repository.name
    if checkout.exists() or checkout.is_symlink():
        if checkout.is_symlink():
            raise AssemblyError(f"locked checkout path must not be a symbolic link: {checkout}")
        shutil.rmtree(checkout)
    checkout.mkdir(parents=True)
    _run_git(["init", "--quiet"], cwd=checkout)
    _run_git(["remote", "add", "origin", repository.repository], cwd=checkout)
    _run_git(["fetch", "--quiet", "--depth=1", "origin", repository.revision], cwd=checkout)
    _run_git(["checkout", "--quiet", "--detach", "FETCH_HEAD"], cwd=checkout)
    actual_revision = _run_git(["rev-parse", "HEAD"], cwd=checkout)
    if actual_revision != repository.revision:
        raise AssemblyError(f"locked checkout revision mismatch for {repository.name}")
    return checkout


def assemble(manifest: Manifest, source_mode: str) -> Path:
    """Create a fresh documentation tree and return its staging path."""
    if source_mode not in {"local", "locked"}:
        raise AssemblyError("source mode must be local or locked")
    if not manifest.content_directory.is_dir():
        raise AssemblyError(f"website content directory is missing: {manifest.content_directory}")
    if manifest.content_directory.is_symlink():
        raise AssemblyError("website content directory must not be a symbolic link")

    if manifest.staging_directory.exists() or manifest.staging_directory.is_symlink():
        if manifest.staging_directory.is_symlink():
            raise AssemblyError("staging directory must not be a symbolic link")
        shutil.rmtree(manifest.staging_directory)
    _copy_tree(manifest.content_directory, manifest.staging_directory)

    for repository in manifest.repositories:
        if source_mode == "local":
            source_root = next(
                (
                    candidate
                    for candidate in repository.local_directories
                    if candidate.is_dir() and (candidate / ".git").exists()
                ),
                None,
            )
            if source_root is None:
                raise AssemblyError(f"local source repository is missing: {repository.name}")
        elif repository.documents:
            source_root = _locked_checkout(manifest, repository)
        else:
            source_root = manifest.root

        for document in repository.documents:
            source = source_root.joinpath(*document.source.parts)
            destination = manifest.staging_directory.joinpath(*document.destination.parts)
            _copy_tree(source, destination)

    metadata_path = manifest.staging_directory / "assets" / "data" / "documentation-sources.json"
    if metadata_path.exists():
        raise AssemblyError("website content must not define generated source metadata")
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata = {
        "schema_version": SCHEMA_VERSION,
        "repositories": [
            {
                "name": repository.name,
                "repository": repository.repository,
                "revision": repository.revision,
            }
            for repository in manifest.repositories
        ],
    }
    metadata_path.write_text(
        f"{json.dumps(metadata, indent=2, sort_keys=True)}\n",
        encoding="utf-8",
        newline="\n",
    )
    return manifest.staging_directory


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("documentation-sources.toml"),
        help="source manifest relative to the current directory",
    )
    parser.add_argument(
        "--source-mode",
        choices=("local", "locked"),
        default="local",
        help="use sibling checkouts or exact remote revisions",
    )
    return parser


def main() -> int:
    """Run the command-line assembler."""
    arguments = _parser().parse_args()
    try:
        manifest = load_manifest(arguments.manifest)
        staging = assemble(manifest, arguments.source_mode)
    except AssemblyError as error:
        print(f"boxferry-website: documentation assembly failed: {error}", file=sys.stderr)
        return 1
    print(f"BoxFerry documentation assembled in {staging.relative_to(manifest.root)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
