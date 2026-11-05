"""Repository-level tests for reproducibility and maintenance contracts."""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.generate_brand_assets import GENERATED_ASSET_PATHS

ROOT = Path(__file__).resolve().parents[1]
ACTION_PATTERN = re.compile(r"uses:\s+[^\s@]+@([0-9a-f]{40})\s+#\s+v?\d")
COLOR_PATTERN = re.compile(r"#[0-9a-fA-F]{3,8}\b|(?:rgb|hsl)a?\(")
EXACT_PYTHON_PIN_PATTERN = re.compile(
    r"(?P<name>[a-z0-9][a-z0-9._-]*)==(?P<version>[0-9][0-9A-Za-z.+-]*)\Z"
)
EXACT_NODE_PIN_PATTERN = re.compile(
    r"[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?\Z"
)


def exact_python_pins(dependencies: list[str]) -> dict[str, str]:
    """Return exact direct pins, rejecting ranges and duplicate package names."""
    pins: dict[str, str] = {}
    for dependency in dependencies:
        match = EXACT_PYTHON_PIN_PATTERN.fullmatch(dependency)
        if match is None:
            raise ValueError(f"Python development dependency is not exactly pinned: {dependency}")

        name = match.group("name")
        if name in pins:
            raise ValueError(f"Python development dependency is pinned more than once: {name}")
        pins[name] = match.group("version")
    return pins


def exact_node_pins(dependencies: dict[str, str]) -> dict[str, str]:
    """Return exact Node pins, rejecting ranges, tags, and other selectors."""
    for name, version in dependencies.items():
        if EXACT_NODE_PIN_PATTERN.fullmatch(version) is None:
            raise ValueError(f"Node development dependency is not exactly pinned: {name}@{version}")
    return dependencies


def validate_eligibility_listener(source: str, manifest: dict) -> None:
    """Allow only the reviewed metadata listener shape, without a YAML parser dependency."""
    revision = manifest["revision"]
    if not re.fullmatch(r"[a-f0-9]{40}", revision):
        raise ValueError("automation authority must contain a full immutable revision")
    expected = f"""---
name: Dependency eligibility service
on:
  workflow_run:
    workflows: [CI]
    types: [requested, completed]
  schedule:
    - cron: "17 * * * *"
permissions:
  actions: write
  contents: read
  pull-requests: read
  statuses: write
jobs:
  eligibility:
    permissions:
      actions: write
      checks: read
      contents: read
      pull-requests: write
      statuses: write
    if: >-
      github.event_name == 'schedule' ||
      (github.event_name == 'workflow_run' &&
      (github.event.workflow_run.event == 'pull_request' ||
      github.event.workflow_run.event == 'merge_group'))
    uses: Strukturpiloten/boxferry/.github/workflows/shared-dependency-eligibility.yml@{revision}
    with:
      automation-sha: {revision}
"""

    def normalized(text: str) -> list[str]:
        return [
            line.split("#", 1)[0].rstrip()
            for line in text.splitlines()
            if line.split("#", 1)[0].strip()
        ]

    if normalized(source) != normalized(expected):
        raise ValueError("eligibility listener must retain the exact metadata-only contract")


class RepositoryPolicyTests(unittest.TestCase):
    """Keep local and hosted quality contracts aligned."""

    def test_zensical_uses_canonical_routes_and_dark_first_palette(self) -> None:
        with (ROOT / "zensical.toml").open("rb") as handle:
            project = tomllib.load(handle)["project"]

        self.assertEqual(project["site_url"], "https://boxferry.dev/")
        self.assertEqual(project["docs_dir"], ".generated/docs")
        self.assertEqual(project["site_dir"], "site")
        self.assertEqual(project["repo_url"], "https://github.com/Strukturpiloten/boxferry")
        self.assertFalse(project["theme"]["font"])
        self.assertEqual(project["theme"]["palette"][0]["scheme"], "slate")
        self.assertEqual(project["theme"]["palette"][1]["scheme"], "default")
        self.assertIn("navigation.indexes", project["theme"]["features"])
        self.assertNotIn("navigation.tabs", project["theme"]["features"])
        self.assertNotIn("navigation.tabs.sticky", project["theme"]["features"])
        self.assertEqual(project["markdown_extensions"]["pymdownx"]["details"], {})
        self.assertEqual(project["markdown_extensions"]["pymdownx"]["superfences"], {})
        self.assertEqual([next(iter(item)) for item in project["nav"]], ["Docs", "Support"])

        custom_dir = project["theme"].get("custom_dir")
        if custom_dir is not None:
            self.assertTrue((ROOT / custom_dir).is_dir())
            tracked_files = subprocess.run(
                [
                    "git",
                    "ls-files",
                    "--cached",
                    "--others",
                    "--exclude-standard",
                    "--",
                    custom_dir,
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.splitlines()
            self.assertTrue(tracked_files)

    def test_conversion_guides_are_grouped_by_input_then_output(self) -> None:
        with (ROOT / "zensical.toml").open("rb") as handle:
            navigation = tomllib.load(handle)["project"]["nav"]

        documentation = next(item["Docs"] for item in navigation if "Docs" in item)
        guides = next(
            item["Guides"] for item in documentation if isinstance(item, dict) and "Guides" in item
        )

        self.assertEqual(
            guides,
            [
                "docs/guides/index.md",
                {
                    "Compose input": [
                        "docs/guides/compose-input/index.md",
                        {"Compose output": "docs/guides/convert/compose-to-compose/index.md"},
                        {"Podman output": "docs/guides/convert/compose-to-podman/index.md"},
                        {"Quadlet output": "docs/guides/convert/compose-to-quadlet/index.md"},
                    ]
                },
                {
                    "Podman input": [
                        "docs/guides/podman-input/index.md",
                        {"Compose output": "docs/guides/convert/podman-to-compose/index.md"},
                        {"Podman output": "docs/guides/convert/podman-to-podman/index.md"},
                        {"Quadlet output": "docs/guides/convert/podman-to-quadlet/index.md"},
                    ]
                },
                {
                    "Quadlet input": [
                        "docs/guides/quadlet-input/index.md",
                        {"Compose output": "docs/guides/convert/quadlet-to-compose/index.md"},
                        {"Podman output": "docs/guides/convert/quadlet-to-podman/index.md"},
                        {"Quadlet output": "docs/guides/convert/quadlet-to-quadlet/index.md"},
                    ]
                },
            ],
        )

    def test_podman_lens_navigation_uses_local_guides_and_public_rustdoc(self) -> None:
        with (ROOT / "zensical.toml").open("rb") as handle:
            navigation = tomllib.load(handle)["project"]["nav"]

        documentation = next(item["Docs"] for item in navigation if "Docs" in item)
        libraries = next(
            item["Libraries"]
            for item in documentation
            if isinstance(item, dict) and "Libraries" in item
        )
        podman_lens = next(
            item["PodmanLens"]
            for item in libraries
            if isinstance(item, dict) and "PodmanLens" in item
        )
        self.assertEqual(
            podman_lens,
            [
                "docs/libraries/podman-lens/index.md",
                {"Acquisition": "docs/libraries/podman-lens/acquisition/index.md"},
                {"Discovery": "docs/libraries/podman-lens/discovery/index.md"},
                {"Grouping": "docs/libraries/podman-lens/grouping/index.md"},
                {
                    "Planning and rendering": (
                        "docs/libraries/podman-lens/planning-rendering/index.md"
                    )
                },
                {
                    "Diagnostics and privacy": (
                        "docs/libraries/podman-lens/diagnostics-privacy/index.md"
                    )
                },
                {"Compatibility": "docs/libraries/podman-lens/compatibility/index.md"},
            ],
        )
        api = next(
            item["API"] for item in documentation if isinstance(item, dict) and "API" in item
        )
        self.assertEqual(
            api,
            [
                "docs/api/index.md",
                {"ComposeLens": "https://boxferry.dev/docs/api/compose-lens/"},
                {"PodmanLens": "https://boxferry.dev/docs/api/podman-lens/"},
                {"QuadletLens": "https://boxferry.dev/docs/api/quadlet-lens/"},
            ],
        )

    def test_boxferry_owns_primary_documentation_sources(self) -> None:
        with (ROOT / "documentation-sources.toml").open("rb") as handle:
            repositories = tomllib.load(handle)["repositories"]

        boxferry = next(
            repository for repository in repositories if repository["name"] == "boxferry"
        )
        self.assertRegex(boxferry["revision"], r"\A[0-9a-f]{40}\Z")
        mappings = {
            (document["source"], document["destination"]) for document in boxferry["documents"]
        }
        self.assertEqual(
            mappings,
            {
                ("docs/public/index.md", "docs/index.md"),
                ("docs/public/getting-started", "docs/getting-started"),
                ("docs/public/guides", "docs/guides"),
                ("docs/public/concepts", "docs/concepts"),
                ("docs/public/reference", "docs/reference"),
                ("docs/public/development", "docs/development"),
                ("docs/documentation-examples.toml", "_data/documentation-examples.toml"),
            },
        )
        for path in (
            "content/docs/index.md",
            "content/docs/getting-started",
            "content/docs/guides",
            "content/docs/concepts",
            "content/docs/reference",
            "content/docs/development",
        ):
            with self.subTest(path=path):
                self.assertFalse((ROOT / path).exists())

    def test_public_writing_contract_is_short_task_oriented_and_executable(self) -> None:
        guidelines = (ROOT / "docs" / "content-guidelines.md").read_text(encoding="utf-8")
        for expected in (
            "finish a task",
            "below 900 words",
            "black-box tests",
            "Do not publish roadmaps",
            "repository that owns behavior owns its technical Markdown",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, guidelines)

        assembler = (ROOT / "scripts" / "assemble_docs.py").read_text(encoding="utf-8")
        for expected in (
            "_verify_documented_commands",
            "_generate_rule_reference",
            "PUBLIC_PAGE_WORD_LIMIT",
            "PLACEHOLDER_PHRASES",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, assembler)

    def test_presentation_entry_points_are_documented_and_regression_checked(self) -> None:
        homepage = (ROOT / "content" / "index.md").read_text(encoding="utf-8")
        site_css = (ROOT / "content" / "assets" / "stylesheets" / "site.css").read_text(
            encoding="utf-8"
        )
        customization = (ROOT / "docs" / "customization.md").read_text(encoding="utf-8")

        template = (ROOT / "overrides" / "home.html").read_text(encoding="utf-8")
        self.assertIn("template: home.html", homepage)
        self.assertIn("'docs/guides/' | url", template)
        self.assertIn(".md-grid", site_css)
        self.assertIn("overrides/home.html", customization)
        for expected in (
            "zensical.toml",
            "content/assets/stylesheets/site.css",
            "content/assets/stylesheets/tokens.css",
            "content/assets/images/brand/",
            "scripts/generate_brand_assets.py",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, customization)

    def test_lenses_own_library_pages_and_first_party_rustdoc(self) -> None:
        with (ROOT / "documentation-sources.toml").open("rb") as handle:
            repositories = tomllib.load(handle)["repositories"]

        self.assertEqual(
            [repository["name"] for repository in repositories],
            ["boxferry", "compose-lens", "podman-lens", "quadlet-lens"],
        )
        for repository in repositories:
            with self.subTest(repository=repository["name"]):
                self.assertRegex(repository["revision"], r"\A[0-9a-f]{40}\Z")

        compose = next(
            repository for repository in repositories if repository["name"] == "compose-lens"
        )
        podman = next(
            repository for repository in repositories if repository["name"] == "podman-lens"
        )
        quadlet = next(
            repository for repository in repositories if repository["name"] == "quadlet-lens"
        )
        self.assertEqual(
            compose["documents"],
            [{"source": "docs/public", "destination": "docs/libraries/compose-lens"}],
        )
        self.assertEqual(
            compose["rustdoc"],
            {
                "package": "compose-lens",
                "crate": "compose_lens",
                "destination": "docs/api/compose-lens",
            },
        )
        self.assertEqual(
            podman["documents"],
            [{"source": "docs/public", "destination": "docs/libraries/podman-lens"}],
        )
        self.assertEqual(
            podman["rustdoc"],
            {
                "package": "podman-lens",
                "crate": "podman_lens",
                "destination": "docs/api/podman-lens",
            },
        )
        self.assertEqual(
            quadlet["documents"],
            [
                {"source": "docs/public", "destination": "docs/libraries/quadlet-lens"},
                {
                    "source": "catalogue/v1/podman-supported-range.toml",
                    "destination": (
                        "docs/libraries/quadlet-lens/catalogue/v1/podman-supported-range.toml"
                    ),
                },
            ],
        )
        self.assertEqual(
            quadlet["rustdoc"],
            {
                "package": "quadlet-lens",
                "crate": "quadlet_lens",
                "destination": "docs/api/quadlet-lens",
            },
        )
        self.assertFalse((ROOT / "content" / "docs" / "libraries" / "compose-lens").exists())
        self.assertFalse((ROOT / "content" / "docs" / "libraries" / "podman-lens").exists())
        self.assertFalse((ROOT / "content" / "docs" / "libraries" / "quadlet-lens").exists())

    def test_company_and_legal_links_are_explicit_and_first_party(self) -> None:
        with (ROOT / "zensical.toml").open("rb") as handle:
            extra = tomllib.load(handle)["project"]["extra"]

        self.assertEqual(
            {key: value for key, value in extra.items() if key != "formats"},
            {
                "contact_url": (
                    "https://www.strukturpiloten.de/kontakt?utm_source=boxferry.dev"
                    "&utm_medium=referral&utm_campaign=boxferry&utm_content=footer_contact"
                ),
                "legal_notice_path": "legal-notice/",
                "privacy_policy_path": "privacy-policy/",
                "strukturpiloten_url": (
                    "https://www.strukturpiloten.de/?utm_source=boxferry.dev"
                    "&utm_medium=referral&utm_campaign=boxferry&utm_content=header_company"
                ),
            },
        )

    def test_header_and_footer_links_use_the_intended_locations(self) -> None:
        header = (ROOT / "overrides" / "partials" / "source.html").read_text(encoding="utf-8")
        footer = (ROOT / "overrides" / "partials" / "copyright.html").read_text(encoding="utf-8")

        self.assertIn("{{ 'docs/' | url }}", header)
        self.assertIn("{{ 'support/' | url }}", header)
        self.assertRegex(
            footer,
            r'(?s)config\.extra\.contact_url.*target="_blank".*rel="noopener noreferrer"',
        )

    def test_english_legal_pages_cover_provider_and_privacy_baselines(self) -> None:
        legal_notice = (ROOT / "content" / "legal-notice" / "index.md").read_text(encoding="utf-8")
        privacy_policy = (ROOT / "content" / "privacy-policy" / "index.md").read_text(
            encoding="utf-8"
        )

        for expected in ("Legal Notice", "Section 5", "HRA 200758", "DE456878137"):
            with self.subTest(document="legal notice", expected=expected):
                self.assertIn(expected, legal_notice)
        self.assertIn('<address class="bf-legal-address">', legal_notice)
        self.assertFalse(any(line.endswith("\\") for line in legal_notice.splitlines()))
        self.assertIn('<address class="bf-legal-address">', privacy_policy)
        self.assertFalse(any(line.endswith("\\") for line in privacy_policy.splitlines()))
        for expected in (
            "Privacy Policy",
            "Hetzner Online GmbH",
            "Article 6(1)(f) GDPR",
            "retention setting in the hosting account",
            "seven days for Apache access and error logs",
            "encrypted backups",
            "does not set cookies",
            "local storage",
            "Section 25(2)(2)",
            "Article 21 GDPR",
        ):
            with self.subTest(document="privacy policy", expected=expected):
                self.assertIn(expected, privacy_policy)

    def test_legal_contacts_and_content_responsibility_are_consistent(self) -> None:
        pages = {
            name: (ROOT / "content" / name / "index.md").read_text(encoding="utf-8")
            for name in ("legal-notice", "privacy-policy")
        }
        for name, page in pages.items():
            with self.subTest(page=name):
                self.assertIn("Strukturpiloten OHG", page)
                self.assertIn(
                    "Represented by its partners: Frauke Beckert and Martin Beckert.", page
                )
                self.assertIn(
                    "[martin.beckert@strukturpiloten.de](mailto:martin.beckert@strukturpiloten.de)",
                    page,
                )
                self.assertIn("[+49 1520 777 1337](tel:+4915207771337)", page)
                self.assertNotIn("hallo@strukturpiloten.de", page)
                self.assertNotIn("4816832", page)
        self.assertIn(
            "Martin Beckert is responsible for the website content", pages["legal-notice"]
        )
        self.assertNotIn("Section 18(2)", pages["legal-notice"])
        self.assertNotIn("documentation tabs", pages["privacy-policy"])
        self.assertNotIn("longer than 14 days", pages["privacy-policy"])
        self.assertIn(
            "These provider defaults do not establish the current setting", pages["privacy-policy"]
        )
        self.assertIn("Last updated: 6 October 2026", pages["privacy-policy"])

    def test_custom_company_icon_is_local_monochrome_and_passive(self) -> None:
        icon = ROOT / "overrides" / ".icons" / "strukturpiloten" / "rocket.svg"
        source = icon.read_text(encoding="utf-8")

        self.assertIn("currentColor", source)
        self.assertIn('aria-hidden="true"', source)
        self.assertNotIn("<script", source.casefold())
        self.assertNotIn("href=", source.casefold())
        self.assertIsNone(COLOR_PATTERN.search(source))

    def test_direct_python_tools_are_exactly_pinned(self) -> None:
        with (ROOT / "pyproject.toml").open("rb") as handle:
            configuration = tomllib.load(handle)
        with (ROOT / "uv.lock").open("rb") as handle:
            lock = tomllib.load(handle)

        dependencies = configuration["dependency-groups"]["dev"]
        configured_pins = exact_python_pins(dependencies)
        self.assertEqual(set(configured_pins), {"zensical", "zizmor"})

        root_package = next(
            package for package in lock["package"] if package["name"] == "boxferry-website"
        )
        locked_requirements = root_package["metadata"]["requires-dev"]["dev"]
        locked_pins = exact_python_pins(
            [
                f"{requirement['name']}{requirement['specifier']}"
                for requirement in locked_requirements
            ]
        )
        self.assertEqual(locked_pins, configured_pins)

        resolved_versions = {
            package["name"]: package["version"]
            for package in lock["package"]
            if package["name"] in configured_pins
        }
        self.assertEqual(resolved_versions, configured_pins)

        self.assertNotIn("uv", configuration["tool"])

    def test_uv_ruff_and_ty_have_one_shared_execution_owner(self) -> None:
        configuration = json.loads((ROOT / ".github/renovate.json").read_text())
        project = tomllib.loads((ROOT / "pyproject.toml").read_text())
        self.assertNotIn("uv", project["tool"])
        self.assertFalse(
            any("ruff==" in pin or "ty==" in pin for pin in project["dependency-groups"]["dev"])
        )
        for name in ("ci.yml", "deploy.yml"):
            workflow = (ROOT / ".github/workflows" / name).read_text()
            self.assertIn("uses: ./_automation/.github/actions/shared-python", workflow)
            if name == "ci.yml":
                self.assertNotIn("astral-sh/setup-uv@", workflow)
            else:
                self.assertIn("version-file: source/pyproject.toml", workflow)
                self.assertIn("checksum: ${{ steps.toolchain.outputs.legacy_checksum }}", workflow)
        self.assertFalse(
            any(
                "/^pyproject\\.toml$/" in manager.get("managerFilePatterns", [])
                for manager in configuration["customManagers"]
            )
        )
        self.assertEqual(len(configuration["extends"]), 1)
        self.assertIn("/renovate-presets/common#", configuration["extends"][0])

    def test_eligibility_listener_is_metadata_only_and_authority_aligned(self) -> None:
        source = (ROOT / ".github/workflows/dependency-eligibility.yml").read_text()
        manifest = json.loads((ROOT / ".github/automation.json").read_text())
        validate_eligibility_listener(source, manifest)
        revision = manifest["revision"]
        permission_scopes = {
            "actions": "write",
            "checks": "read",
            "contents": "read",
            "pull-requests": "write",
            "statuses": "write",
        }
        job_permissions = "    permissions:\n" + "".join(
            f"      {scope}: {level}\n" for scope, level in permission_scopes.items()
        )
        self.assertIn(job_permissions, source)
        permission_mutations = [
            source.replace(job_permissions, "", 1),
            source.replace(job_permissions, job_permissions + "      issues: write\n", 1),
        ]
        for scope, level in permission_scopes.items():
            permission = f"      {scope}: {level}\n"
            wrong_level = "write" if level == "read" else "read"
            permission_mutations.extend(
                (
                    source.replace(permission, "", 1),
                    source.replace(permission, f"      {scope}: {wrong_level}\n", 1),
                )
            )
        mutations = (
            *permission_mutations,
            source.replace("on:", "on:\n  push:", 1),
            source.replace("workflows: [CI]", "workflows: [Release]"),
            source.replace("[requested, completed]", "[in_progress, completed]"),
            source.replace("'pull_request'", "'push'"),
            source.replace("'merge_group'", "'push'"),
            source.replace("17 * * * *", "* * * * *"),
            source.replace("contents: read", "contents: write"),
            source.replace("statuses: write", "statuses: write\n  secrets: write"),
            source.replace("  eligibility:", "  eligibility:\n    continue-on-error: true"),
            source.replace("  eligibility:", "  eligibility:\n    steps:\n      - run: candidate"),
            source.replace(".yml@" + revision, ".yml@" + "b" * 40),
            source.replace("automation-sha: " + revision, "automation-sha: " + "b" * 40),
        )
        for mutation in mutations:
            with self.subTest(source=mutation):
                self.assertNotEqual(mutation, source)
                with self.assertRaises(ValueError):
                    validate_eligibility_listener(mutation, manifest)
        with self.assertRaises(ValueError):
            validate_eligibility_listener(source, {**manifest, "revision": "main"})

    def test_python_pin_parser_rejects_non_exact_and_duplicate_dependencies(self) -> None:
        invalid_dependency_sets = (
            ["ruff>=0.16.3"],
            ["ruff~=0.16.3"],
            ["ruff"],
            ["ruff==0.16.3", "ruff==0.16.4"],
        )

        for dependencies in invalid_dependency_sets:
            with self.subTest(dependencies=dependencies), self.assertRaises(ValueError):
                exact_python_pins(dependencies)

    def test_direct_node_tools_are_exactly_pinned_and_locked(self) -> None:
        package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
        lock = json.loads((ROOT / "package-lock.json").read_text(encoding="utf-8"))

        configured_pins = exact_node_pins(package["devDependencies"])
        self.assertEqual(set(configured_pins), {"cspell", "markdownlint-cli2", "prettier"})

        locked_pins = exact_node_pins(lock["packages"][""]["devDependencies"])
        self.assertEqual(locked_pins, configured_pins)

        resolved_versions = {
            name: lock["packages"][f"node_modules/{name}"]["version"] for name in configured_pins
        }
        self.assertEqual(resolved_versions, configured_pins)

    def test_node_pin_parser_rejects_non_exact_dependencies(self) -> None:
        invalid_versions = ("^10.0.1", "~10.0.1", ">=10.0.1", "latest", "10.0")

        for version in invalid_versions:
            with self.subTest(version=version), self.assertRaises(ValueError):
                exact_node_pins({"cspell": version})

    def test_spelling_gate_covers_repository_sources(self) -> None:
        configuration = json.loads((ROOT / "cspell.json").read_text(encoding="utf-8"))
        self.assertTrue(configuration["useGitignore"])
        self.assertEqual(configuration["language"], "en,en-US")

        file_gate = (ROOT / "scripts" / "check-files.sh").read_text(encoding="utf-8")
        self.assertIn("cspell --config cspell.json", file_gate)
        for extension in ("*.md", "*.py", "*.toml", "*.json", "*.yaml", "*.css", "*.svg"):
            with self.subTest(extension=extension):
                self.assertIn(extension, file_gate)

    def test_tombi_uses_an_offline_pyproject_schema(self) -> None:
        with (ROOT / "tombi.toml").open("rb") as handle:
            configuration = tomllib.load(handle)

        pyproject_schemas = [
            schema for schema in configuration["schemas"] if schema["include"] == ["pyproject.toml"]
        ]
        self.assertEqual(
            pyproject_schemas,
            [
                {
                    "include": ["pyproject.toml"],
                    "path": "docs/schemas/tombi-pyproject-offline.schema.json",
                }
            ],
        )

        schema_path = ROOT / pyproject_schemas[0]["path"]
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        self.assertEqual(schema["type"], "object")
        self.assertTrue(schema["additionalProperties"])

    def test_every_github_action_is_immutable_and_versioned(self) -> None:
        workflows = sorted((ROOT / ".github" / "workflows").glob("*.yml"))
        self.assertTrue(workflows)
        for workflow in workflows:
            uses_lines = [
                line.strip()
                for line in workflow.read_text(encoding="utf-8").splitlines()
                if line.strip().startswith("uses:") or " uses:" in line
            ]
            for line in uses_lines:
                with self.subTest(workflow=workflow.name, line=line):
                    if "uses: ./_automation/.github/actions/" in line:
                        self.assertIn("repository: Strukturpiloten/boxferry", workflow.read_text())
                        if workflow.name == "deploy.yml":
                            self.assertIn(
                                "ref: ${{ steps.toolchain.outputs.automation_sha }}",
                                workflow.read_text(),
                            )
                        else:
                            self.assertIn("currentValue=automation-v1", workflow.read_text())
                    elif "uses: ./.github/workflows/" in line:
                        self.assertEqual(workflow.name, "ci.yml")
                        self.assertEqual(
                            line,
                            "uses: ./.github/workflows/deploy.yml "
                            "# zizmor: ignore[self-repository] -- Same-commit reusable workflow; "
                            "pinned actionlint 1.7.12 lacks $/ support.",
                        )
                    elif "Strukturpiloten/boxferry/.github/workflows/" in line:
                        self.assertRegex(line, r"@[0-9a-f]{40} # automation-v1 interface v1")
                    else:
                        self.assertRegex(line, ACTION_PATTERN)

    def test_renovate_polls_and_merges_documentation_source_revisions(self) -> None:
        configuration = json.loads((ROOT / ".github/renovate.json").read_text())
        manager = next(
            manager
            for manager in configuration["customManagers"]
            if manager.get("datasourceTemplate") == "git-refs"
        )
        matches = list(
            re.finditer(
                manager["matchStrings"][0].replace("(?<", "(?P<"),
                (ROOT / "documentation-sources.toml").read_text(),
            )
        )
        self.assertEqual(
            [match.group("depName") for match in matches],
            [
                "Strukturpiloten/boxferry",
                "Strukturpiloten/compose-lens",
                "Strukturpiloten/podman-lens",
                "Strukturpiloten/quadlet-lens",
            ],
        )
        self.assertEqual(manager["packageNameTemplate"], "{{depName}}")
        rule = next(
            rule
            for rule in configuration["packageRules"]
            if rule.get("matchDatasources") == ["git-refs"]
        )
        self.assertEqual(rule["matchFileNames"], ["documentation-sources.toml"])
        self.assertEqual(rule["minimumReleaseAge"], "0 days")
        self.assertEqual(
            rule["matchPackageNames"],
            [match.group("depName") for match in matches],
        )
        self.assertTrue(rule["automerge"])

    def test_renovate_defers_shared_eligibility_without_local_manual_overrides(self) -> None:
        configuration = json.loads((ROOT / ".github/renovate.json").read_text())
        for rule in configuration["packageRules"]:
            self.assertIsNot(rule.get("automerge"), False)
            self.assertIsNot(rule.get("dependencyDashboardApproval"), True)
        manifest = json.loads((ROOT / ".github/automation.json").read_text())
        self.assertEqual(
            configuration["extends"],
            [f"github>Strukturpiloten/boxferry//renovate-presets/common#{manifest['revision']}"],
        )

    def test_native_file_tools_have_one_canonical_inventory_owner(self) -> None:
        installer = (ROOT / "scripts/install-file-tools.sh").read_text()
        self.assertIn('shared-ci.py" tools', installer)
        self.assertIn("--profile website", installer)
        self.assertIn("--tools lychee", installer)
        for obsolete in ("readonly lychee_version", "lychee_checksum", "curl --", "# renovate:"):
            self.assertNotIn(obsolete, installer)
        configuration = json.loads((ROOT / ".github/renovate.json").read_text())
        self.assertFalse(
            any(
                "install-file-tools" in pattern
                for manager in configuration["customManagers"]
                for pattern in manager["managerFilePatterns"]
            )
        )

    def test_deployment_workflow_preserves_static_release_contract(self) -> None:
        deployment = (ROOT / ".github/workflows/deploy.yml").read_text()
        ci = (ROOT / ".github/workflows/ci.yml").read_text()
        for expected in (
            "workflow_dispatch:",
            "name: production",
            "./scripts/check-all.sh",
            "BOXFERRY_WEBSITE_SOURCE_MODE: locked",
            "include-hidden-files: true",
            "inputs.revision || github.sha",
            "python3 scripts/select_deployment_request.py",
            "--check-current",
            "steps.current.outputs.current == 'true'",
            "rsync -rlptz --delete --safe-links",
            "activate %s %s",
            "bootstrap %s %s",
            "finalize %s",
        ):
            self.assertIn(expected, deployment)
        for expected in (
            "workflow_call:",
            "inputs.automatic == true && github.event_name == 'push'",
            "github.ref == 'refs/heads/main'",
            "AUTOMATIC_DEPLOYMENT: ${{ inputs.automatic || false }}",
            "automatic: ${{ steps.normalize.outputs.automatic }}",
            "cancel-in-progress: false",
        ):
            self.assertIn(expected, deployment)
        for forbidden in (
            "pull_request:",
            "pull_request_target:",
            "workflow_run:",
            "actions: write",
        ):
            self.assertNotIn(forbidden, deployment)
        publish = deployment.split("\n  deploy:\n", 1)[1].split("\n  rollback:\n", 1)[0]
        self.assertLess(publish.index("--check-current"), publish.index("Download immutable"))
        self.assertLess(publish.index("--check-current"), publish.index("secrets."))
        self.assertEqual(publish.count("steps.current.outputs.current == 'true'"), 4)
        for forbidden in (
            "statuses: write",
            "actions: write",
            "pull_request_target:",
            "production:",
            "inputs[operation]=deploy",
        ):
            self.assertNotIn(forbidden, ci)
        publish_call = ci.split("\n  publish-site:\n", 1)[1]
        for expected in (
            "needs: [pr-gate]",
            "needs.pr-gate.result == 'success'",
            "github.event_name == 'push' && github.ref == 'refs/heads/main'",
            "uses: ./.github/workflows/deploy.yml",
            "revision: ${{ github.sha }}",
            "operation: deploy",
            "automatic: true",
        ):
            self.assertIn(expected, publish_call)
        self.assertNotIn("secrets:", ci.split("\n  publish-site:\n", 1)[0])
        self.assertNotIn("secrets: inherit", ci)
        self.assertIn(
            "cancel-in-progress: ${{ github.event_name == 'pull_request' || "
            "github.event_name == 'merge_group' }}",
            ci,
        )
        self.assertIn("BOXFERRY_WEBSITE_SOURCE_MODE: locked", ci)
        self.assertIn("shared-dependency-wait.yml@", ci)
        self.assertIn("name: Dependency eligibility", ci)
        self.assertIn("merge_group:", ci)
        for permission in ("contents: read", "actions: read", "statuses: read"):
            self.assertIn(permission, ci)

    def test_reusable_publisher_receives_only_named_deployment_credentials(self) -> None:
        ci = (ROOT / ".github/workflows/ci.yml").read_text()
        deployment = (ROOT / ".github/workflows/deploy.yml").read_text()
        names = {"BOXFERRY_RSYNC_SSH_PRIVATE_KEY", "BOXFERRY_VERSION_UPDATER_SSH_PRIVATE_KEY"}
        publish = ci.split("\n  publish-site:\n", 1)[1]
        forwarded = publish.split("    secrets:\n", 1)[1].split("    with:\n", 1)[0]
        self.assertEqual(
            {line.strip() for line in forwarded.splitlines() if line.strip()},
            {f"{name}: ${{{{ secrets.{name} }}}}" for name in names},
        )
        self.assertNotIn("secrets: inherit", ci)
        self.assertNotIn("secrets:", ci.split("\n  publish-site:\n", 1)[0])
        called = deployment.split("  workflow_call:\n", 1)[1]
        declared = called.split("    secrets:\n", 1)[1].split("  workflow_dispatch:", 1)[0]
        self.assertEqual(set(re.findall(r"^      ([A-Z_]+):$", declared, re.MULTILINE)), names)
        self.assertEqual(declared.count("required: false"), 2)
        publisher = deployment.split("\n  deploy:\n", 1)[1].split("\n  rollback:\n", 1)[0]
        self.assertIn("name: production", publisher)
        for name in names:
            self.assertIn(f"${{{{ secrets.{name} }}}}", publisher)

    def test_main_push_publication_has_a_distinct_concurrency_lane(self) -> None:
        workflow = (ROOT / ".github/workflows/ci.yml").read_text()
        group = next(line.strip() for line in workflow.splitlines() if line.startswith("  group:"))
        groups = {
            event: group.replace("${{ github.workflow }}", "CI")
            .replace("${{ github.event_name }}", event)
            .replace("${{ github.ref }}", "refs/heads/main")
            for event in ("push", "workflow_dispatch")
        }
        self.assertNotEqual(groups["push"], groups["workflow_dispatch"])
        self.assertNotIn("${{", groups["push"])
        self.assertIn(
            "cancel-in-progress: ${{ github.event_name == 'pull_request' || "
            "github.event_name == 'merge_group' }}",
            workflow,
        )

    def test_required_ci_is_the_unique_always_running_validation_aggregate(self) -> None:
        workflow = (ROOT / ".github/workflows/ci.yml").read_text()
        gate = workflow.split("\n  pr-gate:\n", 1)[1]
        self.assertIn("    name: Required CI\n", gate)
        self.assertIn("    if: always()\n", gate)
        self.assertIn("    needs: [validation-plan, quality, lockfile-release-age]\n", gate)
        self.assertIn("python -m boxferry_ci gate", gate)
        self.assertIn("PLAN_JSON: ${{ needs.validation-plan.outputs.plan }}", gate)
        self.assertIn("NEEDS_JSON: ${{ toJSON(needs) }}", gate)
        self.assertIn('--plan-json "${PLAN_JSON}" --needs-json "${NEEDS_JSON}"', gate)
        self.assertNotIn("continue-on-error:", gate)
        self.assertNotIn("        if:", gate)
        self.assertEqual(workflow.count("name: Required CI"), 1)

    def test_shared_callers_bind_all_candidate_policy_and_implementation_identities(self) -> None:
        workflow = (ROOT / ".github/workflows/ci.yml").read_text()
        for expected in (
            '--event "${EVENT_NAME}"',
            '--tested-sha "${GITHUB_SHA}"',
            '--policy-sha "${POLICY_SHA}"',
            '--automation-sha "${AUTOMATION_SHA}"',
            "github.event.pull_request.base.sha || github.event.merge_group.base_sha || github.sha",
            "uses: ./_automation/.github/actions/shared-source",
            "uses: ./_automation/.github/actions/shared-python",
            "python -m boxferry_ci run-local",
            "--report-json",
            "if: always()",
            "website-validation-${{ github.sha }}",
        ):
            self.assertIn(expected, workflow)
        service = (ROOT / ".github/workflows/dependency-eligibility.yml").read_text()
        self.assertIn("workflows: [CI]", service)
        self.assertIn("types: [requested, completed]", service)
        self.assertIn("schedule:", service)
        self.assertNotIn("pull_request_target:", service)
        self.assertNotIn("actions/checkout", service)
        self.assertIn("shared-dependency-eligibility.yml@", service)

    def test_literal_colors_are_centralized(self) -> None:
        token_file = ROOT / "content" / "assets" / "stylesheets" / "tokens.css"
        generated_assets = {ROOT / path for path in GENERATED_ASSET_PATHS}
        candidates = [
            *ROOT.glob("content/**/*.css"),
            *ROOT.glob("content/**/*.html"),
            *ROOT.glob("content/**/*.svg"),
            *ROOT.glob("docs/**/*.svg"),
            *ROOT.glob("overrides/**/*.html"),
        ]
        for path in candidates:
            if path == token_file or path in generated_assets:
                continue
            with self.subTest(path=path.relative_to(ROOT)):
                self.assertIsNone(COLOR_PATTERN.search(path.read_text(encoding="utf-8")))

    def test_generated_and_temporary_paths_are_ignored(self) -> None:
        for path in (
            "temp/documentation-plan.md",
            ".generated/docs/index.md",
            "site/index.html",
            ".venv/bin/python",
            "node_modules/prettier/index.js",
        ):
            with self.subTest(path=path):
                result = subprocess.run(
                    ["git", "check-ignore", "--quiet", path],
                    cwd=ROOT,
                    check=False,
                )
                self.assertEqual(result.returncode, 0)

    def test_vscode_exposes_complete_check_build_and_preview(self) -> None:
        tasks = json.loads((ROOT / ".vscode" / "tasks.json").read_text(encoding="utf-8"))["tasks"]
        labels = {task["label"] for task in tasks}
        self.assertIn("BoxFerry Website: Format, lint, test, and build", labels)
        self.assertIn("BoxFerry Website: Build", labels)
        self.assertIn("BoxFerry Website: Preview", labels)

    def test_complete_gate_covers_every_repository_language(self) -> None:
        gate = (ROOT / "scripts" / "check-all.sh").read_text(encoding="utf-8")
        for expected in (
            "--task python-format",
            "generate_brand_assets.py",
            "scripts/check-files.sh",
            "cspell",
            "actionlint",
            "zizmor",
            "--task python-quality",
            "--task automation-policy",
            "unittest discover",
            "assemble_docs.py",
            "zensical build",
            "build_rustdoc.py",
            "publish_ai_docs.py",
            "prepare_deployment.py",
            "verify_site.py",
            '[[ -f "${markdown_file}" ]]',
            "lychee",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, gate)

    def test_complete_yaml_documents_use_explicit_start_markers(self) -> None:
        documents = sorted(
            [*ROOT.glob("**/*.yaml"), *ROOT.glob("**/*.yml")],
        )
        documents = [
            path
            for path in documents
            if not any(
                part
                in {
                    ".generated",
                    ".venv",
                    "node_modules",
                    "site",
                    "temp",
                }
                for part in path.relative_to(ROOT).parts
            )
        ]
        self.assertTrue(documents)
        for document in documents:
            with self.subTest(document=document.relative_to(ROOT)):
                first_line = document.read_text(encoding="utf-8").splitlines()[0]
                self.assertEqual(first_line, "---")

    def test_yaml_policy_covers_checkout_below_generated_ancestor(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / ".generated" / "worktrees" / "repository"
            root.mkdir(parents=True)
            owned_documents = (root / "owned.yaml", root / "config" / "owned.yml")
            for document in owned_documents:
                document.parent.mkdir(parents=True, exist_ok=True)
                document.write_text("---\nvalue: owned\n", encoding="utf-8")
            for excluded in (".generated", ".venv", "node_modules", "site", "temp"):
                directory = root / "nested" / excluded
                directory.mkdir(parents=True)
                for suffix in ("yaml", "yml"):
                    (directory / f"excluded.{suffix}").write_text(
                        "missing marker\n", encoding="utf-8"
                    )

            policy = RepositoryPolicyTests(
                "test_complete_yaml_documents_use_explicit_start_markers"
            )
            with patch(f"{__name__}.ROOT", root):
                policy.test_complete_yaml_documents_use_explicit_start_markers()
                for document in owned_documents:
                    with self.subTest(document=document.relative_to(root)):
                        document.write_text("missing marker\n---\n", encoding="utf-8")
                        with self.assertRaises(AssertionError):
                            policy.test_complete_yaml_documents_use_explicit_start_markers()
                        document.write_text("---\nvalue: owned\n", encoding="utf-8")
                for document in owned_documents:
                    document.unlink()
                with self.assertRaises(AssertionError):
                    policy.test_complete_yaml_documents_use_explicit_start_markers()


if __name__ == "__main__":
    unittest.main()
