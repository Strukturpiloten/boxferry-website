#!/usr/bin/env python3
"""Publish deterministic, source-linked Markdown discovery for assembled documentation."""

from __future__ import annotations

import argparse
import html
import re
from dataclasses import dataclass
from pathlib import Path

if __package__:
    from scripts.assemble_docs import Manifest, load_manifest
else:
    from assemble_docs import Manifest, load_manifest

ORIGIN = "https://boxferry.dev"
FULL_LIMIT = 2 * 1024 * 1024
INDEX_LIMIT = 256 * 1024
HEADING = re.compile(r"^# (.+)$", re.MULTILINE)
HEAD_CLOSE = re.compile(r"</head\s*>", re.IGNORECASE)


class AiDocsError(RuntimeError):
    """The assembled documentation cannot be safely published."""


@dataclass(frozen=True)
class Page:
    """One authored Markdown page with stable public routes."""

    source: Path
    relative: Path
    title: str
    repository: str

    @property
    def html_route(self) -> Path:
        if self.relative.name == "index.md":
            return self.relative.with_suffix(".html")
        return self.relative.with_suffix("") / "index.html"

    @property
    def markdown_route(self) -> Path:
        return self.relative


def _owner(relative: Path, manifest: Manifest) -> str:
    for repository in manifest.repositories:
        for mapping in repository.documents:
            destination = Path(*mapping.destination.parts)
            if relative == destination or relative.is_relative_to(destination):
                return repository.name
    return "boxferry-website"


def pages(staging: Path, manifest: Manifest) -> tuple[Page, ...]:
    """Enumerate only assembled authored Markdown, not API HTML or generated rules."""
    result: list[Page] = []
    for source in sorted((staging / "docs").rglob("*.md")):
        relative = source.relative_to(staging)
        if source.is_symlink() or (
            "api" in relative.parts[1:-1] and relative != Path("docs/api/index.md")
        ):
            raise AiDocsError(f"unexpected API Markdown or symlink: {relative}")
        if relative.parts[:4] == ("docs", "reference", "diagnostics", "rules"):
            continue  # Generated from the checked catalogue, not authored Markdown.
        body = source.read_text(encoding="utf-8")
        heading = HEADING.search(re.sub(r"```.*?```", "", body, flags=re.DOTALL))
        if heading is None:
            raise AiDocsError(f"authored documentation has no title: {relative}")
        result.append(Page(source, relative, heading.group(1).strip(), _owner(relative, manifest)))
    if not any(page.relative == Path("docs/index.md") for page in result):
        raise AiDocsError("assembled documentation must contain docs/index.md")
    if len({page.html_route for page in result}) != len(result):
        raise AiDocsError("authored documentation has duplicate HTML routes")
    return tuple(result)


def _link(page: Page) -> str:
    url = f"{ORIGIN}/{page.markdown_route.as_posix()}"
    return f"- [{page.title}]({url}): Markdown alternative for /{page.html_route.as_posix()}"


def indexes(published: tuple[Page, ...], manifest: Manifest) -> dict[Path, str]:
    """Build compact indexes and an optional bounded full-text corpus."""
    provenance = [
        (
            f"- [{source.name}]({source.repository.removesuffix('.git')}/tree/"
            f"{source.revision}): `{source.revision}`"
        )
        for source in manifest.repositories
    ]
    intro = (
        "# BoxFerry\n\n"
        "> Source-aware conversion documentation for Compose, Podman resources, and Quadlet.\n\n"
        "The human-readable site is https://boxferry.dev/docs/. These links are Markdown "
        "alternatives from the same assembled documentation build.\n\n"
    )
    sections: dict[str, list[Page]] = {}
    for page in published:
        section = page.relative.parts[1] if len(page.relative.parts) > 2 else "overview"
        sections.setdefault(section, []).append(page)
    docs_lines = [intro, "## Exact source revisions\n", *provenance, "", "## Documentation\n"]
    for section, entries in sorted(sections.items()):
        docs_lines.extend((f"### {section.replace('-', ' ').title()}\n", *map(_link, entries), ""))
    docs_index = "\n".join(docs_lines).rstrip() + "\n"
    if len(docs_index.encode("utf-8")) > INDEX_LIMIT:
        raise AiDocsError("/docs/llms.txt exceeds its 256 KiB index budget")
    highlights = [
        page
        for page in published
        if page.relative.as_posix()
        in {
            "docs/index.md",
            "docs/getting-started/index.md",
            "docs/guides/index.md",
            "docs/reference/index.md",
            "docs/libraries/index.md",
            "docs/sources/index.md",
        }
    ]
    root_lines = [
        intro,
        "## Start here\n",
        *map(_link, highlights),
        "",
        "## More documentation\n",
        "- [Complete documentation index](https://boxferry.dev/docs/llms.txt): "
        "All authored pages and exact source revisions.",
        "",
    ]
    full_lines = [intro, "## Exact source revisions\n", *provenance, ""]
    for page in published:
        full_lines.extend(
            (
                f"## {page.title}",
                f"Source: {page.repository}; {ORIGIN}/{page.markdown_route.as_posix()}",
                "",
                page.source.read_text(encoding="utf-8").rstrip(),
                "",
            )
        )
    full = "\n".join(full_lines).rstrip() + "\n"
    output = {Path("llms.txt"): "\n".join(root_lines), Path("docs/llms.txt"): docs_index}
    if len(full.encode("utf-8")) <= FULL_LIMIT:
        output[Path("llms-full.txt")] = full
        output[Path("llms.txt")] += (
            "## Optional\n\n- [Full authored corpus](https://boxferry.dev/llms-full.txt): "
            "Bounded assembled Markdown.\n"
        )
    return output


def _html_with_links(source: str, page: Page) -> str:
    alternative = html.escape(f"/{page.markdown_route.as_posix()}", quote=True)
    links = (
        f'<link rel="alternate" type="text/markdown" href="{alternative}">\n'
        '<link rel="describedby" href="/docs/llms.txt">\n'
    )
    match = HEAD_CLOSE.search(source)
    if match is None:
        raise AiDocsError(f"rendered documentation has no head: {page.html_route}")
    return source[: match.start()] + links + source[match.start() :]


def publish(staging: Path, site: Path, manifest: Manifest, *, check: bool = False) -> None:
    """Write or verify the exact derived Markdown routes and HTML discovery links."""
    published = pages(staging, manifest)
    expected: dict[Path, str] = indexes(published, manifest)
    for page in published:
        expected[page.markdown_route] = page.source.read_text(encoding="utf-8")
        html_path = site / page.html_route
        if not html_path.is_file():
            raise AiDocsError(f"rendered documentation route is missing: {page.html_route}")
        current = html_path.read_text(encoding="utf-8")
        if check:
            links = (
                f'<link rel="alternate" type="text/markdown" '
                f'href="/{page.markdown_route.as_posix()}">\n'
                '<link rel="describedby" href="/docs/llms.txt">\n'
            )
            if (
                current.count(links) != 1
                or current.count('rel="alternate" type="text/markdown"') != 1
            ):
                raise AiDocsError(
                    f"Markdown discovery links are missing or stale: {page.html_route}"
                )
        else:
            html_path.write_text(_html_with_links(current, page), encoding="utf-8", newline="\n")
    if check:
        actual_routes = {p.relative_to(site) for p in site.rglob("*.md") if p.is_file()}
        rustdoc_roots = tuple(
            Path(*repository.rustdoc.destination.parts)
            for repository in manifest.repositories
            if repository.rustdoc is not None
        )
        authored_routes = {
            route
            for route in actual_routes
            if not any(route.is_relative_to(root) for root in rustdoc_roots)
        }
        if authored_routes != {p.markdown_route for p in published}:
            raise AiDocsError("published Markdown alternatives are missing or stale")
        actual_indexes = {p.relative_to(site) for p in site.glob("*llms*.txt")}
        actual_indexes.update(p.relative_to(site) for p in (site / "docs").glob("*llms*.txt"))
        if actual_indexes != {p for p in expected if p.suffix == ".txt"}:
            raise AiDocsError("LLM index routes are missing or stale")
        for route, content in expected.items():
            if (site / route).read_text(encoding="utf-8") != content:
                raise AiDocsError(f"published Markdown or index is stale: {route}")
    else:
        for route, content in expected.items():
            destination = site / route
            if destination.exists():
                raise AiDocsError(f"built site already defines a generated Markdown route: {route}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(content, encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("documentation-sources.toml"))
    parser.add_argument("--site", type=Path, default=Path("site"))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        manifest = load_manifest(args.manifest)
        publish(manifest.staging_directory, args.site, manifest, check=args.check)
    except (AiDocsError, OSError) as error:
        parser.exit(1, f"boxferry-website: AI documentation failed: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
