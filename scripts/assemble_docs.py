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
PACKAGE_NAME_PATTERN = re.compile(r"[a-z][a-z0-9-]*")
CRATE_NAME_PATTERN = re.compile(r"[a-z][a-z0-9_]*")
GITHUB_PREFIX = "https://github.com/Strukturpiloten/"
RULE_CODE_PATTERN = re.compile(r"(?:BFC|BFO|BFP|BFQ)[0-9]{4}")
RULE_NAME_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
EXAMPLE_ID_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
RULE_INDEX_MARKER = "<!-- boxferry-generated-rule-index -->"
PUBLIC_PAGE_WORD_LIMIT = 900
PUBLIC_PARAGRAPH_WORD_LIMIT = 120
PLACEHOLDER_PHRASES = (
    "coming soon",
    "final guide will",
    "placeholder",
    "this guide will",
    "this page will",
    "this section will",
)
EXPECTED_SUCCESSFUL_ROUTES = frozenset(
    {
        "compose->compose",
        "compose->podman",
        "compose->quadlet",
        "podman->compose",
        "podman->podman",
        "podman->quadlet",
        "quadlet->compose",
        "quadlet->podman",
        "quadlet->quadlet",
    }
)
EXPECTED_FAILING_ROUTES = frozenset(
    {
        "compose->compose",
        "compose->quadlet",
        "podman->compose",
        "quadlet->compose",
        "quadlet->quadlet",
    }
)


class AssemblyError(RuntimeError):
    """Describe an invalid manifest or unsafe source tree."""


@dataclass(frozen=True)
class DocumentMapping:
    """Map one repository path into one public documentation path."""

    source: PurePosixPath
    destination: PurePosixPath


@dataclass(frozen=True)
class RustdocMapping:
    """Publish one crate's generated API at a stable first-party route."""

    package: str
    crate: str
    destination: PurePosixPath


@dataclass(frozen=True)
class RepositorySource:
    """Describe one exact external documentation source."""

    name: str
    repository: str
    revision: str
    local_directories: tuple[Path, ...]
    documents: tuple[DocumentMapping, ...]
    rustdoc: RustdocMapping | None


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

        raw_rustdoc = table.get("rustdoc")
        rustdoc = None
        if raw_rustdoc is not None:
            rustdoc_label = f"{label}.rustdoc"
            rustdoc_table = _required_mapping(raw_rustdoc, rustdoc_label)
            package = _required_string(rustdoc_table, "package", rustdoc_label)
            crate = _required_string(rustdoc_table, "crate", rustdoc_label)
            destination = _safe_relative_path(
                _required_string(rustdoc_table, "destination", rustdoc_label),
                f"{rustdoc_label}.destination",
            )
            if not PACKAGE_NAME_PATTERN.fullmatch(package):
                raise AssemblyError(f"{rustdoc_label}.package must be a Cargo package slug")
            if not CRATE_NAME_PATTERN.fullmatch(crate):
                raise AssemblyError(f"{rustdoc_label}.crate must be a Rust crate slug")
            expected_destination = PurePosixPath("docs", "api", name)
            if destination != expected_destination:
                raise AssemblyError(f"{rustdoc_label}.destination must be {expected_destination}")
            if destination in destinations:
                raise AssemblyError(f"duplicate documentation destination: {destination}")
            destinations.add(destination)
            rustdoc = RustdocMapping(
                package=package,
                crate=crate,
                destination=destination,
            )

        repositories.append(
            RepositorySource(
                name=name,
                repository=repository,
                revision=revision,
                local_directories=local_directories,
                documents=tuple(documents),
                rustdoc=rustdoc,
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


def _single_line_string(table: dict[str, Any], key: str, label: str) -> str:
    value = _required_string(table, key, label)
    if "\n" in value or "\r" in value:
        raise AssemblyError(f"{label}.{key} must stay on one line")
    return value


def _load_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise AssemblyError(f"cannot read {label}: {error}") from error
    return _required_mapping(value, label)


def _generate_rule_reference(staging: Path) -> None:
    rules_path = staging / "docs" / "reference" / "diagnostics" / "rules.json"
    if not rules_path.exists():
        return
    catalogue = _load_json_object(rules_path, "diagnostic rule catalogue")
    if catalogue.get("schema_version") != 1:
        raise AssemblyError("diagnostic rule catalogue schema_version must be 1")
    raw_rules = catalogue.get("rules")
    if not isinstance(raw_rules, list) or not raw_rules:
        raise AssemblyError("diagnostic rule catalogue must contain rules")

    rules: list[dict[str, str]] = []
    codes: set[str] = set()
    names: set[str] = set()
    for index, raw_rule in enumerate(raw_rules, start=1):
        label = f"diagnostic rule catalogue rules[{index}]"
        rule = _required_mapping(raw_rule, label)
        values = {
            key: _single_line_string(rule, key, label)
            for key in ("code", "name", "default_severity", "description", "help", "owner")
        }
        if not RULE_CODE_PATTERN.fullmatch(values["code"]):
            raise AssemblyError(f"{label}.code is not a BoxFerry rule code")
        if not RULE_NAME_PATTERN.fullmatch(values["name"]):
            raise AssemblyError(f"{label}.name is not a rule slug")
        if values["code"] in codes or values["name"] in names:
            raise AssemblyError(f"duplicate diagnostic rule code or name: {values['code']}")
        codes.add(values["code"])
        names.add(values["name"])
        rules.append(values)

    ordered_codes = [rule["code"] for rule in rules]
    if ordered_codes != sorted(ordered_codes):
        raise AssemblyError("diagnostic rule catalogue must be sorted by code")

    index_path = staging / "docs" / "reference" / "diagnostics" / "index.md"
    try:
        index_text = index_path.read_text(encoding="utf-8")
    except OSError as error:
        raise AssemblyError(f"cannot read diagnostic index: {error}") from error
    if index_text.count(RULE_INDEX_MARKER) != 1:
        raise AssemblyError("diagnostic index must contain one generated-rule marker")

    grouped: dict[str, list[dict[str, str]]] = {}
    for rule in rules:
        grouped.setdefault(rule["owner"], []).append(rule)
    index_lines = [
        "## Rule catalogue",
        "",
        "[Download the machine-readable catalogue](rules.json).",
    ]
    for owner, owner_rules in grouped.items():
        index_lines.extend(("", f"### {owner}", ""))
        index_lines.extend(
            f"- [`{rule['code']}` — {rule['name']}](rules/{rule['code']}/)" for rule in owner_rules
        )
    index_path.write_text(
        index_text.replace(RULE_INDEX_MARKER, "\n".join(index_lines)),
        encoding="utf-8",
        newline="\n",
    )

    rule_root = index_path.parent / "rules"
    if rule_root.exists():
        raise AssemblyError("source documentation must not define generated rule pages")
    for rule in rules:
        page = rule_root / rule["code"] / "index.md"
        page.parent.mkdir(parents=True)
        page.write_text(
            "\n".join(
                (
                    f"# {rule['code']}: {rule['name']}",
                    "",
                    f"**Severity:** `{rule['default_severity']}`  ",
                    f"**Owner:** {rule['owner']}",
                    "",
                    rule["description"],
                    "",
                    "## Fix",
                    "",
                    rule["help"],
                    "",
                    "[Back to all diagnostic rules](../../)",
                    "",
                )
            ),
            encoding="utf-8",
            newline="\n",
        )


def _verify_documented_commands(staging: Path) -> None:
    manifest_path = staging / "_data" / "documentation-examples.toml"
    if not manifest_path.exists():
        return
    try:
        with manifest_path.open("rb") as handle:
            manifest = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise AssemblyError(f"cannot read documentation example manifest: {error}") from error
    if manifest.get("schema") != 1:
        raise AssemblyError("documentation example schema must be 1")
    raw_examples = manifest.get("examples")
    if not isinstance(raw_examples, list) or not raw_examples:
        raise AssemblyError("documentation example manifest must contain examples")

    identifiers: set[str] = set()
    successful_routes: set[str] = set()
    failing_routes: set[str] = set()
    for index, raw_example in enumerate(raw_examples, start=1):
        label = f"documentation examples[{index}]"
        example = _required_mapping(raw_example, label)
        identifier = _single_line_string(example, "id", label)
        if not EXAMPLE_ID_PATTERN.fullmatch(identifier) or identifier in identifiers:
            raise AssemblyError(f"{label}.id must be a unique lowercase slug")
        identifiers.add(identifier)
        command = _single_line_string(example, "command", label)
        args = _required_string_list(example, "args", label)
        if command != f"boxferry {' '.join(args)}":
            raise AssemblyError(f"{label}.command must match its argument array")
        pages = _required_string_list(example, "pages", label)
        expected_exit = example.get("expected-exit")
        if not isinstance(expected_exit, int) or isinstance(expected_exit, bool):
            raise AssemblyError(f"{label}.expected-exit must be an integer")
        block = f"<!-- boxferry-example: {identifier} -->\n\n```console\n{command}\n```"
        for page_value in pages:
            source_page = _safe_relative_path(page_value, f"{label}.pages")
            if source_page.parts[:2] != ("docs", "public"):
                raise AssemblyError(f"{label}.pages must stay below docs/public")
            destination = staging.joinpath("docs", *source_page.parts[2:])
            try:
                page_text = destination.read_text(encoding="utf-8")
            except OSError as error:
                raise AssemblyError(
                    f"cannot read documented command page: {destination}"
                ) from error
            if page_text.count(block) != 1:
                raise AssemblyError(
                    f"{destination} must contain one checked `{identifier}` command"
                )

        if len(args) >= 3 and args[0] == "convert":
            route = f"{args[1]}->{args[2]}"
            if expected_exit == 0:
                successful_routes.add(route)
            else:
                failing_routes.add(route)

    if successful_routes != EXPECTED_SUCCESSFUL_ROUTES or failing_routes != EXPECTED_FAILING_ROUTES:
        raise AssemblyError(
            "documented command route matrix mismatch: "
            f"successful={sorted(successful_routes)}; failing={sorted(failing_routes)}"
        )

    manifest_path.unlink()
    data_directory = manifest_path.parent
    if not any(data_directory.iterdir()):
        data_directory.rmdir()


def _verify_public_content(staging: Path) -> None:
    documentation_root = staging / "docs"
    if not (documentation_root / "index.md").exists():
        return
    public_roots = (
        documentation_root / "index.md",
        documentation_root / "getting-started",
        documentation_root / "guides",
        documentation_root / "concepts",
        documentation_root / "reference",
        documentation_root / "libraries",
        documentation_root / "development",
    )
    files: list[Path] = []
    for root in public_roots:
        if root.is_file():
            files.append(root)
        elif root.is_dir():
            files.extend(sorted(root.rglob("*.md")))
    for path in files:
        text = path.read_text(encoding="utf-8")
        relative = path.relative_to(staging)
        if len(re.findall(r"(?u)\b[\w'-]+\b", text)) > PUBLIC_PAGE_WORD_LIMIT:
            raise AssemblyError(f"public page exceeds {PUBLIC_PAGE_WORD_LIMIT} words: {relative}")
        without_code = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
        if sum(line.startswith("# ") for line in without_code.splitlines()) != 1:
            raise AssemblyError(
                f"public page must contain exactly one level-one heading: {relative}"
            )
        folded = text.casefold()
        for phrase in PLACEHOLDER_PHRASES:
            if phrase in folded:
                raise AssemblyError(
                    f"public page contains placeholder phrase `{phrase}`: {relative}"
                )

        for paragraph in re.split(r"\n\s*\n", without_code):
            stripped = paragraph.strip()
            if not stripped or stripped.startswith(("#", "-", "|", "<")):
                continue
            words = re.findall(r"(?u)\b[\w'-]+\b", stripped)
            if len(words) > PUBLIC_PARAGRAPH_WORD_LIMIT:
                raise AssemblyError(
                    f"public paragraph exceeds {PUBLIC_PARAGRAPH_WORD_LIMIT} words: {relative}"
                )


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

    _generate_rule_reference(manifest.staging_directory)
    _verify_documented_commands(manifest.staging_directory)
    _verify_public_content(manifest.staging_directory)

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
