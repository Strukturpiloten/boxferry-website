"""Guard production caller provenance, exact revisions, and safe supersession."""

from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.select_deployment_request import (
    DeploymentRequest,
    DeploymentRequestError,
    check_current,
    main,
    select_request,
    verify_ancestry,
)

REVISION = "0123456789abcdef0123456789abcdef01234567"
HISTORICAL = "a" * 40
REPOSITORY = "Strukturpiloten/boxferry-website"


def automatic_event() -> dict[str, object]:
    """Supply the caller's same-repository main push payload."""
    return {
        "ref": "refs/heads/main",
        "repository": {"full_name": REPOSITORY},
        "deleted": False,
        "after": REVISION,
    }


def select(
    event: object,
    *,
    event_name: str = "push",
    ref: str = "refs/heads/main",
    repository: str = REPOSITORY,
    github_sha: str = REVISION,
    main_revision: str = REVISION,
    automatic: str = "true",
    requested_operation: str | None = "deploy",
    requested_revision: str | None = REVISION,
) -> DeploymentRequest:
    """Specify the reusable workflow's independently supplied caller context."""
    return select_request(
        event,
        event_name=event_name,
        ref=ref,
        repository=repository,
        github_sha=github_sha,
        main_revision=main_revision,
        automatic=automatic,
        requested_operation=requested_operation,
        requested_revision=requested_revision,
    )


def manual(inputs: object, *, github_sha: str = REVISION) -> DeploymentRequest:
    """Exercise the documented event-input fallback for manual pure selection."""
    return select(
        {"inputs": inputs},
        event_name="workflow_dispatch",
        github_sha=github_sha,
        automatic="false",
        requested_operation=None,
        requested_revision=None,
    )


class DeploymentSelectionTests(unittest.TestCase):
    """Select automatic deploy only for an exact same-repository main push."""

    def test_main_push_selects_exact_requested_deploy(self) -> None:
        result = select(automatic_event())
        self.assertEqual(
            (result.operation, result.revision, result.automatic), ("deploy", REVISION, True)
        )

    def test_superseded_push_is_safe_skip(self) -> None:
        result = select(automatic_event(), main_revision=HISTORICAL)
        self.assertEqual((result.operation, result.revision, result.automatic), ("skip", "", True))
        self.assertIn("superseded", result.summary)

    def test_wrong_branch_fork_deleted_and_revision_payloads_are_rejected(self) -> None:
        for field, value in (
            ("ref", "refs/heads/feature"),
            ("ref", "refs/tags/main"),
            ("repository", {"full_name": "attacker/boxferry-website"}),
            ("repository", {}),
            ("repository", None),
            ("deleted", True),
            ("deleted", "false"),
            ("deleted", 0),
            ("after", HISTORICAL),
            ("after", None),
        ):
            with self.subTest(field=field, value=value):
                event = automatic_event()
                event[field] = value
                with self.assertRaises(DeploymentRequestError):
                    select(event)

    def test_automatic_cannot_bootstrap_rollback_or_select_a_different_revision(self) -> None:
        for operation in ("bootstrap", "rollback", "show-authorized-keys", "", None):
            with self.subTest(operation=operation), self.assertRaises(DeploymentRequestError):
                select(automatic_event(), requested_operation=operation)
        for revision in (HISTORICAL, "main", "", None, REVISION + "\n"):
            with self.subTest(revision=revision), self.assertRaises(DeploymentRequestError):
                select(automatic_event(), requested_revision=revision)
        event = automatic_event()
        event["inputs"] = {"operation": "bootstrap", "revision": HISTORICAL}
        self.assertEqual(select(event).operation, "deploy")

    def test_only_push_is_accepted_as_automatic_caller_event(self) -> None:
        for event_name in (
            "pull_request",
            "pull_request_target",
            "merge_group",
            "workflow_dispatch",
            "workflow_run",
            "workflow_call",
            "schedule",
            "",
        ):
            with self.subTest(event_name=event_name), self.assertRaises(DeploymentRequestError):
                select(automatic_event(), event_name=event_name)
        for ref in ("refs/heads/feature", "refs/tags/main", "", "main"):
            with self.subTest(ref=ref), self.assertRaises(DeploymentRequestError):
                select(automatic_event(), ref=ref)
        with self.assertRaises(DeploymentRequestError):
            select(automatic_event(), repository="")

    def test_unknown_automatic_flags_fail_closed(self) -> None:
        for automatic in ("", "True", "False", "1", "yes", "false\n"):
            with self.subTest(automatic=automatic), self.assertRaises(DeploymentRequestError):
                select(automatic_event(), automatic=automatic)
        with self.assertRaises(DeploymentRequestError):
            select(automatic_event(), automatic="false")

    def test_malformed_events_are_rejected(self) -> None:
        for event in (None, [], "secret", {}, {"repository": []}, {1: "invalid"}):
            with self.subTest(event=event), self.assertRaises(DeploymentRequestError):
                select(event)

    def test_invalid_context_and_main_revisions_are_rejected(self) -> None:
        for revision in ("main", REVISION.upper(), REVISION[:7], REVISION + "\n", "g" * 40, ""):
            with self.subTest(revision=revision):
                with self.assertRaises(DeploymentRequestError):
                    select(automatic_event(), github_sha=revision, requested_revision=revision)
                with self.assertRaises(DeploymentRequestError):
                    select(automatic_event(), main_revision=revision)

    def test_manual_operations_default_to_exact_context_revision(self) -> None:
        for operation in ("show-authorized-keys", "bootstrap", "deploy"):
            with self.subTest(operation=operation):
                result = manual({"operation": operation}, github_sha=HISTORICAL)
                self.assertEqual(result.operation, operation)
                self.assertEqual(result.revision, HISTORICAL)
                self.assertFalse(result.automatic)

    def test_manual_passed_inputs_take_precedence_over_event_inputs(self) -> None:
        result = select(
            {"inputs": {"operation": "bootstrap", "revision": "bad"}},
            event_name="workflow_dispatch",
            automatic="false",
            requested_operation="rollback",
            requested_revision=HISTORICAL,
        )
        self.assertEqual((result.operation, result.revision), ("rollback", HISTORICAL))
        self.assertFalse(result.automatic)

    def test_manual_deploy_and_rollback_accept_historical_revision(self) -> None:
        for operation in ("deploy", "rollback"):
            with self.subTest(operation=operation):
                result = manual({"operation": operation, "revision": HISTORICAL})
                self.assertEqual((result.operation, result.revision), (operation, HISTORICAL))
                self.assertFalse(result.automatic)

    def test_manual_invalid_operations_and_revisions_are_rejected(self) -> None:
        invalid_inputs = (
            {},
            {"operation": "skip"},
            {"operation": "deploy\noperation=bootstrap"},
            {"operation": "rollback"},
            {"operation": "rollback", "revision": ""},
            {"operation": "bootstrap", "revision": HISTORICAL},
            {"operation": "show-authorized-keys", "revision": HISTORICAL},
            {"operation": "deploy", "revision": "main"},
            {"operation": "deploy", "revision": None},
            {"operation": "deploy", "revision": True},
            {"operation": False},
            None,
        )
        for inputs in invalid_inputs:
            with self.subTest(inputs=inputs), self.assertRaises(DeploymentRequestError):
                manual(inputs)
        with self.assertRaises(DeploymentRequestError):
            manual({"operation": "deploy"}, github_sha="main")

    def test_freshness_uses_only_exact_revision_equality(self) -> None:
        self.assertTrue(check_current(REVISION, REVISION))
        self.assertFalse(check_current(HISTORICAL, REVISION))
        for candidate, current in (("main", REVISION), (REVISION, "main")):
            with (
                self.subTest(candidate=candidate, current=current),
                self.assertRaises(DeploymentRequestError),
            ):
                check_current(candidate, current)


class DeploymentAncestryTests(unittest.TestCase):
    """Exercise actual Git ancestry without executing anything from a candidate."""

    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.repository = Path(temporary.name)
        self.git("init", "--quiet")
        self.git("commit", "--allow-empty", "--quiet", "-m", "root")
        self.historical = self.git("rev-parse", "HEAD")
        self.git("commit", "--allow-empty", "--quiet", "-m", "main")
        self.current = self.git("rev-parse", "HEAD")
        self.git("checkout", "--quiet", "--detach", self.historical)
        self.git("commit", "--allow-empty", "--quiet", "-m", "side_branch")
        self.side_branch = self.git("rev-parse", "HEAD")

    def git(self, *arguments: str) -> str:
        return subprocess.run(
            ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", *arguments],
            cwd=self.repository,
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.strip()

    def test_current_and_historical_ancestors_are_accepted(self) -> None:
        for revision in (self.current, self.historical):
            with self.subTest(revision=revision):
                verify_ancestry(revision, self.current, repository_root=self.repository)

    def test_missing_commit_and_side_branch_revision_are_rejected(self) -> None:
        for revision in ("f" * 40, self.side_branch):
            with self.subTest(revision=revision), self.assertRaises(DeploymentRequestError):
                verify_ancestry(revision, self.current, repository_root=self.repository)
        with self.assertRaises(DeploymentRequestError):
            verify_ancestry(self.historical, "f" * 40, repository_root=self.repository)

    def test_git_timeout_fails_closed(self) -> None:
        with (
            patch(
                "scripts.select_deployment_request.subprocess.run",
                side_effect=subprocess.TimeoutExpired("git", 10),
            ),
            self.assertRaises(DeploymentRequestError),
        ):
            verify_ancestry(REVISION, REVISION, repository_root=self.repository)


class DeploymentRequestCliTests(unittest.TestCase):
    """Check exact safe outputs and rejection behavior at the workflow boundary."""

    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.event_path = self.root / "event.json"
        self.output = self.root / "output"
        self.summary = self.root / "summary"
        self.arguments = [
            "--main-revision",
            REVISION,
            "--github-output",
            str(self.output),
            "--summary",
            str(self.summary),
        ]
        self.environment = {
            "GITHUB_EVENT_PATH": str(self.event_path),
            "GITHUB_EVENT_NAME": "push",
            "AUTOMATIC_DEPLOYMENT": "true",
            "REQUESTED_OPERATION": "deploy",
            "REQUESTED_REVISION": REVISION,
            "GITHUB_REF": "refs/heads/main",
            "GITHUB_REPOSITORY": REPOSITORY,
            "GITHUB_SHA": REVISION,
        }
        self.event_path.write_text(json.dumps(automatic_event()), encoding="utf-8")

    def invoke(self, *extra_arguments: str) -> int:
        with patch.dict(os.environ, self.environment, clear=True):
            return main([*self.arguments, *extra_arguments])

    def test_success_appends_exact_outputs_after_ancestry_verification(self) -> None:
        self.output.write_text("prior=value\n", encoding="utf-8")
        with patch("scripts.select_deployment_request.verify_ancestry") as ancestry:
            self.assertEqual(self.invoke(), 0)
        ancestry.assert_called_once_with(REVISION, REVISION)
        self.assertEqual(
            self.output.read_text(encoding="utf-8"),
            f"prior=value\noperation=deploy\nrevision={REVISION}\nautomatic=true\n",
        )
        self.assertIn(REVISION, self.summary.read_text(encoding="utf-8"))

    def test_stale_run_skips_without_git_or_candidate_execution(self) -> None:
        self.arguments[1] = HISTORICAL
        with patch("scripts.select_deployment_request.verify_ancestry") as ancestry:
            self.assertEqual(self.invoke(), 0)
        ancestry.assert_not_called()
        self.assertEqual(
            self.output.read_text(encoding="utf-8"), "operation=skip\nrevision=\nautomatic=true\n"
        )
        self.assertIn("superseded", self.summary.read_text(encoding="utf-8"))

    def test_manual_historical_deploy_verifies_selected_revision(self) -> None:
        self.environment["GITHUB_EVENT_NAME"] = "workflow_dispatch"
        self.environment["AUTOMATIC_DEPLOYMENT"] = "false"
        self.environment["REQUESTED_OPERATION"] = "deploy"
        self.environment["REQUESTED_REVISION"] = HISTORICAL
        self.event_path.write_text(
            json.dumps({"inputs": {"operation": "deploy", "revision": HISTORICAL}}),
            encoding="utf-8",
        )
        with patch("scripts.select_deployment_request.verify_ancestry") as ancestry:
            self.assertEqual(self.invoke(), 0)
        ancestry.assert_called_once_with(HISTORICAL, REVISION)
        self.assertEqual(
            self.output.read_text(encoding="utf-8"),
            f"operation=deploy\nrevision={HISTORICAL}\nautomatic=false\n",
        )

    def test_ancestry_failure_writes_no_publish_outputs(self) -> None:
        with (
            patch(
                "scripts.select_deployment_request.verify_ancestry",
                side_effect=DeploymentRequestError("revision must exist"),
            ),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            self.assertEqual(self.invoke(), 1)
        self.assertFalse(self.output.exists())
        self.assertFalse(self.summary.exists())

    def test_freshness_ignores_event_metadata_and_ancestry(self) -> None:
        self.environment = {}
        self.event_path.unlink()
        with patch("scripts.select_deployment_request.verify_ancestry") as ancestry:
            self.assertEqual(self.invoke("--check-current", "--revision", HISTORICAL), 0)
        ancestry.assert_not_called()
        self.assertEqual(self.output.read_text(encoding="utf-8"), "current=false\n")
        self.assertIn("superseded", self.summary.read_text(encoding="utf-8"))
        self.output.unlink()
        self.assertEqual(self.invoke("--check-current", "--revision", REVISION), 0)
        self.assertEqual(self.output.read_text(encoding="utf-8"), "current=true\n")

    def test_malformed_json_and_secret_values_do_not_leak(self) -> None:
        for payload in ("PRIVATE_WEBHOOK_SECRET", '{"inputs":"PRIVATE_WEBHOOK_SECRET"}'):
            with self.subTest(payload=payload):
                self.event_path.write_text(payload, encoding="utf-8")
                stderr = io.StringIO()
                with contextlib.redirect_stderr(stderr):
                    self.assertEqual(self.invoke(), 1)
                self.assertNotIn("PRIVATE_WEBHOOK_SECRET", stderr.getvalue())
                self.assertFalse(self.output.exists())

    def test_invalid_cli_modes_fail_without_outputs(self) -> None:
        for arguments in (
            ("--check-current",),
            ("--revision", REVISION),
            ("--check-current", "--revision", "main"),
        ):
            with self.subTest(arguments=arguments), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(self.invoke(*arguments), 1)
                self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
