"""Repository-local agent roles and complete check-only gate contracts."""

import subprocess
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class AgentConfigurationTests(unittest.TestCase):
    def test_primary_and_bounded_defaults(self) -> None:
        config = tomllib.loads((ROOT / ".codex/config.toml").read_text(encoding="utf-8"))
        self.assertEqual(config["model"], "gpt-6-astra")
        self.assertEqual(config["model_reasoning_effort"], "high")
        self.assertTrue(config["agents"]["enabled"])
        self.assertEqual(config["agents"]["max_concurrent_threads_per_session"], 3)
        self.assertEqual(config["agents"]["default_subagent_model"], "gpt-5.6-terra")
        self.assertEqual(config["agents"]["default_subagent_reasoning_effort"], "medium")

    def test_explicit_roles_and_permissions(self) -> None:
        for role, model, effort, sandbox in (
            ("implementation-worker", "gpt-5.6-terra", "high", "workspace-write"),
            ("specification-researcher", "gpt-5.6-terra", "high", "read-only"),
            ("reviewer", "gpt-5.6-sol", "high", "read-only"),
            ("verifier", "gpt-5.6-terra", "medium", "workspace-write"),
        ):
            with self.subTest(role=role):
                config = tomllib.loads(
                    (ROOT / f".codex/agents/{role}.toml").read_text(encoding="utf-8")
                )
                self.assertEqual(config["name"], role.replace("-", "_"))
                self.assertEqual(config["model"], model)
                self.assertEqual(config["model_reasoning_effort"], effort)
                self.assertEqual(config["sandbox_mode"], sandbox)
                instructions = config["developer_instructions"]
                self.assertIn("AGENTS.md", instructions)
                self.assertIn("GitHub writes", instructions)
                if role == "reviewer":
                    self.assertIn("original user requirements", instructions)
                    self.assertIn("independent expected results", instructions)
                if role == "verifier":
                    self.assertIn("./scripts/check-all.sh --check", instructions)
                    self.assertIn("never run the default formatting gate", instructions)

    def test_governance_is_model_independent(self) -> None:
        instructions = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        for model in ("Astra", "Sol", "Terra"):
            self.assertNotIn(model, instructions)

    def test_gate_modes_and_failure_propagation(self) -> None:
        result = subprocess.run(
            ["bash", "scripts/test-check-all.sh"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
