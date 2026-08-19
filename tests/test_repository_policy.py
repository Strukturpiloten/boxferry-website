"""Repository-level tests for reproducibility and maintenance contracts."""

from __future__ import annotations

import json
import re
import subprocess
import tomllib
import unittest
from pathlib import Path

from scripts.generate_brand_assets import GENERATED_ASSET_PATHS

ROOT = Path(__file__).resolve().parents[1]
ACTION_PATTERN = re.compile(r"uses:\s+[^\s@]+@([0-9a-f]{40})\s+#\s+v?\d")
COLOR_PATTERN = re.compile(r"#[0-9a-fA-F]{3,8}\b|(?:rgb|hsl)a?\(")


class RepositoryPolicyTests(unittest.TestCase):
    """Keep local and hosted quality contracts aligned."""

    def test_zensical_uses_canonical_routes_and_dark_first_palette(self) -> None:
        with (ROOT / "zensical.toml").open("rb") as handle:
            project = tomllib.load(handle)["project"]

        self.assertEqual(project["site_url"], "https://boxferry.dev/")
        self.assertEqual(project["docs_dir"], ".generated/docs")
        self.assertEqual(project["site_dir"], "site")
        self.assertEqual(project["repo_url"], "https://github.com/Strukturpiloten/boxferry")
        self.assertEqual(project["theme"]["palette"][0]["scheme"], "slate")
        self.assertEqual(project["theme"]["palette"][1]["scheme"], "default")
        self.assertIn("navigation.indexes", project["theme"]["features"])

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

        documentation = next(
            item["Documentation"] for item in navigation if "Documentation" in item
        )
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
                        {"Quadlet output": "docs/guides/convert/compose-to-quadlet/index.md"},
                    ]
                },
                {
                    "Quadlet input": [
                        "docs/guides/quadlet-input/index.md",
                        {"Compose output": "docs/guides/convert/quadlet-to-compose/index.md"},
                        {"Quadlet output": "docs/guides/convert/quadlet-to-quadlet/index.md"},
                    ]
                },
            ],
        )

    def test_boxferry_owns_primary_documentation_sources(self) -> None:
        with (ROOT / "documentation-sources.toml").open("rb") as handle:
            repositories = tomllib.load(handle)["repositories"]

        boxferry = next(
            repository for repository in repositories if repository["name"] == "boxferry"
        )
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

    def test_lenses_own_library_pages_and_first_party_rustdoc(self) -> None:
        with (ROOT / "documentation-sources.toml").open("rb") as handle:
            repositories = tomllib.load(handle)["repositories"]

        compose = next(
            repository for repository in repositories if repository["name"] == "compose-lens"
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
        self.assertFalse((ROOT / "content" / "docs" / "libraries" / "quadlet-lens").exists())

    def test_company_and_legal_links_are_explicit_and_first_party(self) -> None:
        with (ROOT / "zensical.toml").open("rb") as handle:
            extra = tomllib.load(handle)["project"]["extra"]

        self.assertEqual(
            extra,
            {
                "contact_url": "https://www.strukturpiloten.de/kontakt",
                "legal_notice_path": "legal-notice/",
                "privacy_policy_path": "privacy-policy/",
                "strukturpiloten_url": "https://www.strukturpiloten.de/",
            },
        )

    def test_english_legal_pages_cover_provider_and_privacy_baselines(self) -> None:
        legal_notice = (ROOT / "content" / "legal-notice" / "index.md").read_text(encoding="utf-8")
        privacy_policy = (ROOT / "content" / "privacy-policy" / "index.md").read_text(
            encoding="utf-8"
        )

        for expected in ("Legal Notice", "Section 5", "HRA 200758", "DE456878137"):
            with self.subTest(document="legal notice", expected=expected):
                self.assertIn(expected, legal_notice)
        for expected in (
            "Privacy Policy",
            "Hetzner Online GmbH",
            "Article 6(1)(f) GDPR",
            "14 days",
            "does not set cookies",
            "local storage",
            "Section 25(2)(2)",
            "Article 21 GDPR",
        ):
            with self.subTest(document="privacy policy", expected=expected):
                self.assertIn(expected, privacy_policy)

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

        dependencies = configuration["dependency-groups"]["dev"]
        self.assertEqual(
            dependencies,
            ["ruff==0.16.3", "zensical==0.0.56", "zizmor==1.28.0"],
        )
        self.assertEqual(configuration["tool"]["uv"]["required-version"], "==0.12.5")

    def test_spelling_gate_is_pinned_and_covers_repository_sources(self) -> None:
        package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
        self.assertEqual(package["devDependencies"]["cspell"], "10.0.1")

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
                    self.assertRegex(line, ACTION_PATTERN)

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
            "ruff format",
            "generate_brand_assets.py",
            "scripts/check-files.sh",
            "cspell",
            "actionlint",
            "zizmor",
            "ruff check",
            "unittest discover",
            "assemble_docs.py",
            "zensical build",
            "build_rustdoc.py",
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
                part in {".generated", ".venv", "node_modules", "site", "temp"}
                for part in path.parts
            )
        ]
        self.assertTrue(documents)
        for document in documents:
            with self.subTest(document=document.relative_to(ROOT)):
                first_line = document.read_text(encoding="utf-8").splitlines()[0]
                self.assertEqual(first_line, "---")


if __name__ == "__main__":
    unittest.main()
