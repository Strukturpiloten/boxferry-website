#!/usr/bin/env python3
"""Select an exact, eligible production request without executing candidate code."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import cast

REVISION_PATTERN = re.compile(r"[0-9a-f]{40}")
OPERATIONS = frozenset({"show-authorized-keys", "bootstrap", "deploy", "rollback"})
ROOT = Path(__file__).resolve().parents[1]


class DeploymentRequestError(RuntimeError):
    """Describe an ineligible or malformed deployment request without event contents."""


@dataclass(frozen=True)
class DeploymentRequest:
    """Validated operation and immutable revision, or an automatic safe skip."""

    operation: str
    revision: str
    automatic: bool
    summary: str


def validate_revision(revision: str) -> str:
    """Require a complete lowercase Git object identifier."""
    if not REVISION_PATTERN.fullmatch(revision):
        raise DeploymentRequestError("revision must be exactly 40 lowercase hex digits")
    return revision


def object_field(value: object) -> Mapping[str, object]:
    """Reject non-object JSON values at a trusted boundary."""
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise DeploymentRequestError("event contains a missing or malformed object")
    return cast("Mapping[str, object]", value)


def string_field(value: object) -> str:
    """Reject non-string JSON values rather than coercing input."""
    if not isinstance(value, str):
        raise DeploymentRequestError("event contains a missing or malformed string")
    return value


def select_request(
    event: object,
    *,
    event_name: str,
    ref: str,
    repository: str,
    github_sha: str,
    main_revision: str,
    automatic: str = "false",
    requested_operation: str | None = None,
    requested_revision: str | None = None,
) -> DeploymentRequest:
    """Select from trusted caller context and untrusted event data without I/O."""
    validate_revision(main_revision)
    if automatic not in {"true", "false"}:
        raise DeploymentRequestError("automatic deployment must be true or false")
    if ref != "refs/heads/main":
        raise DeploymentRequestError("production requests require refs/heads/main")
    if not repository:
        raise DeploymentRequestError("repository context is required")
    payload = object_field(event)
    if automatic == "false":
        if event_name != "workflow_dispatch":
            raise DeploymentRequestError("manual requests require workflow_dispatch")
        inputs = object_field(payload.get("inputs", {}))
        operation = (
            requested_operation
            if requested_operation is not None
            else string_field(inputs.get("operation"))
        )
        revision_input = (
            requested_revision
            if requested_revision is not None
            else string_field(inputs.get("revision", ""))
        )
        if operation not in OPERATIONS:
            raise DeploymentRequestError("manual operation is not supported")
        if revision_input and operation not in {"deploy", "rollback"}:
            raise DeploymentRequestError("only deploy and rollback accept an explicit revision")
        if operation == "rollback" and not revision_input:
            raise DeploymentRequestError("rollback requires an explicit revision")
        revision = validate_revision(revision_input or github_sha)
        return DeploymentRequest(operation, revision, False, f"Manual {operation}: `{revision}`.\n")
    if event_name != "push":
        raise DeploymentRequestError("automatic requests require a main push")
    event_repository = object_field(payload.get("repository"))
    revision = validate_revision(github_sha)
    eligible = (
        payload.get("ref") == "refs/heads/main"
        and payload.get("deleted", False) is False
        and event_repository.get("full_name") == repository
        and payload.get("after") == revision
        and requested_operation == "deploy"
        and requested_revision == revision
    )
    if not eligible:
        raise DeploymentRequestError(
            "automatic request must deploy the exact same-repository main push"
        )
    if revision != main_revision:
        return DeploymentRequest(
            "skip", "", True, "Automatic deployment skipped: push revision is superseded.\n"
        )
    return DeploymentRequest("deploy", revision, True, f"Automatic deploy: `{revision}`.\n")


def check_current(revision: str, main_revision: str) -> bool:
    """Compare exact candidate and freshly acquired main revisions without I/O."""
    return validate_revision(revision) == validate_revision(main_revision)


def verify_ancestry(revision: str, main_revision: str, *, repository_root: Path = ROOT) -> None:
    """Require existing commits and main ancestry using bounded read-only Git calls."""
    validate_revision(revision)
    validate_revision(main_revision)
    commands = (
        ["git", "cat-file", "-e", f"{revision}^{{commit}}"],
        ["git", "cat-file", "-e", f"{main_revision}^{{commit}}"],
        ["git", "merge-base", "--is-ancestor", revision, main_revision],
    )
    try:
        for command in commands:
            subprocess.run(
                command,
                cwd=repository_root,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=10,
            )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        raise DeploymentRequestError(
            "revision must exist and be an ancestor of current main"
        ) from error


def append_result(output: Path, summary: Path, values: Mapping[str, str], message: str) -> None:
    """Append only validated output fields and bounded explanatory text."""
    with output.open("a", encoding="utf-8") as stream:
        for key, value in values.items():
            stream.write(f"{key}={value}\n")
    with summary.open("a", encoding="utf-8") as stream:
        stream.write(message)


def main(argv: list[str] | None = None) -> int:
    """Validate a request or recheck freshness before protected publication."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--main-revision", required=True)
    parser.add_argument("--github-output", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--check-current", action="store_true")
    parser.add_argument("--revision")
    arguments = parser.parse_args(argv)
    try:
        if arguments.check_current:
            if arguments.revision is None:
                raise DeploymentRequestError("freshness check requires an exact revision")
            current = check_current(arguments.revision, arguments.main_revision)
            append_result(
                arguments.github_output,
                arguments.summary,
                {"current": str(current).lower()},
                "Deployment revision is current main.\n"
                if current
                else "Deployment skipped: revision is superseded by current main.\n",
            )
            return 0
        if arguments.revision is not None:
            raise DeploymentRequestError("--revision requires --check-current")
        event_path = os.environ.get("GITHUB_EVENT_PATH")
        if not event_path:
            raise DeploymentRequestError("event path is required")
        event: object = json.loads(Path(event_path).read_text(encoding="utf-8"))
        request = select_request(
            event,
            event_name=os.environ.get("GITHUB_EVENT_NAME", ""),
            ref=os.environ.get("GITHUB_REF", ""),
            repository=os.environ.get("GITHUB_REPOSITORY", ""),
            github_sha=os.environ.get("GITHUB_SHA", ""),
            main_revision=arguments.main_revision,
            automatic=os.environ.get("AUTOMATIC_DEPLOYMENT", "false"),
            requested_operation=os.environ.get("REQUESTED_OPERATION"),
            requested_revision=os.environ.get("REQUESTED_REVISION"),
        )
        if request.operation != "skip":
            verify_ancestry(request.revision, arguments.main_revision)
        append_result(
            arguments.github_output,
            arguments.summary,
            {
                "operation": request.operation,
                "revision": request.revision,
                "automatic": str(request.automatic).lower(),
            },
            request.summary,
        )
    except (DeploymentRequestError, OSError, ValueError) as error:
        # Never print exceptions from JSON/file parsing, which may contain webhook data or paths.
        message = (
            str(error)
            if isinstance(error, DeploymentRequestError)
            else "cannot read or write request data"
        )
        print(f"boxferry-website: deployment request rejected: {message}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
