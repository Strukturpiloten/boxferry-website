"""Offline contracts for deterministic, privacy-safe AI documentation routes."""

from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path, PurePosixPath

from scripts.assemble_docs import DocumentMapping, Manifest, RepositorySource, RustdocMapping
from scripts.publish_ai_docs import FULL_LIMIT, AiDocsError, indexes, pages, publish

REVISION = "0123456789abcdef0123456789abcdef01234567"


class PublishAiDocsTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.staging = self.root / ".generated" / "docs"
        self.site = self.root / "site"
        self.manifest = Manifest(
            root=self.root,
            content_directory=self.root / "content",
            staging_directory=self.staging,
            repositories=(
                RepositorySource(
                    name="boxferry",
                    repository="https://github.com/Strukturpiloten/boxferry.git",
                    revision=REVISION,
                    local_directories=(),
                    documents=(
                        DocumentMapping(PurePosixPath("docs/public"), PurePosixPath("docs")),
                    ),
                    rustdoc=None,
                ),
            ),
        )
        self.add_page("docs/index.md", "# BoxFerry docs\n\nWelcome.\n")
        self.add_page("docs/guides/alpha/index.md", "# Alpha\n\nFirst guide.\n")
        self.add_page("docs/guides/zeta/index.md", "# Zeta\n\nLast guide.\n")

    def add_page(self, relative: str, body: str) -> None:
        source = self.staging / relative
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(body, encoding="utf-8")
        html = self.site / Path(relative).with_suffix(".html")
        html.parent.mkdir(parents=True, exist_ok=True)
        html.write_text(
            "<!doctype html><html><head><title>Page</title></head><body></body></html>",
            encoding="utf-8",
        )

    def test_publish_is_deterministic_and_has_exact_source_provenance(self) -> None:
        publish(self.staging, self.site, self.manifest)
        publish(self.staging, self.site, self.manifest, check=True)
        index = (self.site / "docs/llms.txt").read_text(encoding="utf-8")
        self.assertLess(index.index("Alpha"), index.index("Zeta"))
        self.assertIn(REVISION, index)
        self.assertNotIn(str(self.root), index)
        self.assertIn("/docs/guides/alpha/index.md", index)
        root = (self.site / "llms.txt").read_text(encoding="utf-8")
        self.assertTrue(root.startswith("# BoxFerry\n\n>"))
        self.assertIn("## Optional", root)
        self.assertIn("First guide.", (self.site / "llms-full.txt").read_text(encoding="utf-8"))
        html = (self.site / "docs/guides/alpha/index.html").read_text(encoding="utf-8")
        self.assertIn('rel="alternate" type="text/markdown"', html)
        self.assertIn('rel="describedby" href="/docs/llms.txt"', html)

    def test_modified_or_missing_alternative_is_rejected(self) -> None:
        publish(self.staging, self.site, self.manifest)
        (self.site / "docs/guides/alpha/index.md").write_text("stale\n", encoding="utf-8")
        with self.assertRaisesRegex(AiDocsError, "stale"):
            publish(self.staging, self.site, self.manifest, check=True)

    def test_stale_extra_route_is_rejected(self) -> None:
        publish(self.staging, self.site, self.manifest)
        (self.site / "docs/stale.md").write_text("# Old\n", encoding="utf-8")
        with self.assertRaisesRegex(AiDocsError, "missing or stale"):
            publish(self.staging, self.site, self.manifest, check=True)

    def test_rustdoc_bundled_markdown_is_not_an_authored_alternative(self) -> None:
        repository = replace(
            self.manifest.repositories[0],
            rustdoc=RustdocMapping(
                package="boxferry",
                crate="boxferry",
                destination=PurePosixPath("docs/api/boxferry"),
            ),
        )
        manifest = replace(self.manifest, repositories=(repository,))
        publish(self.staging, self.site, manifest)
        license_page = self.site / "docs/api/boxferry/static.files/LICENSE.md"
        license_page.parent.mkdir(parents=True)
        license_page.write_text("# Bundled Rustdoc license\n", encoding="utf-8")

        publish(self.staging, self.site, manifest, check=True)

        (self.site / "docs/api/unmapped.md").write_text("# Stale\n", encoding="utf-8")
        with self.assertRaisesRegex(AiDocsError, "missing or stale"):
            publish(self.staging, self.site, manifest, check=True)

    def test_missing_html_discovery_is_rejected(self) -> None:
        publish(self.staging, self.site, self.manifest)
        page = self.site / "docs/index.html"
        page.write_text(
            page.read_text(encoding="utf-8").replace('rel="describedby"', 'rel="help"'),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(AiDocsError, "discovery links"):
            publish(self.staging, self.site, self.manifest, check=True)

    def test_generated_rule_pages_are_not_republished(self) -> None:
        rule = self.staging / "docs/reference/diagnostics/rules/BFC0001/index.md"
        rule.parent.mkdir(parents=True)
        rule.write_text("# Generated rule\n", encoding="utf-8")
        self.assertNotIn(rule, [page.source for page in pages(self.staging, self.manifest)])

    def test_full_corpus_is_omitted_after_bound_without_losing_index(self) -> None:
        published = pages(self.staging, self.manifest)
        # Source text is read at index-generation time; simulate a large authored corpus.
        published[-1].source.write_text("# Zeta\n\n" + "a" * FULL_LIMIT, encoding="utf-8")
        result = indexes(pages(self.staging, self.manifest), self.manifest)
        self.assertNotIn(Path("llms-full.txt"), result)
        self.assertIn(Path("docs/llms.txt"), result)
        self.assertNotIn("## Optional", result[Path("llms.txt")])


if __name__ == "__main__":
    unittest.main()
