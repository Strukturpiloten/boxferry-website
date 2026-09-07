# 0004: Signal identity and scalable format discovery

- Status: Accepted
- Date: 2026-09-07
- Supersedes: [0002](0002-token-derived-vector-identity.md)

## Context

The website review found an oversized homepage, a complex small logo, and a dark documentation
link color below the documented contrast threshold. The maintainer selected the Signal direction:
charcoal and lime, a centered introduction, a clear command example, and the Exchange mark.

The format set will grow beyond Compose, Podman resources, and Quadlet. Docker resources and
Kubernetes are planned; Helm remains undecided. A homepage with one link for every source/target
pair would grow to 25 or 36 links and repeat much of the conversion-guide navigation.

## Decision

Use Signal and its monochrome Exchange mark. Retain the centralized token file, deterministic
brand generator, stable asset paths, system fonts, dark-first theme, and selectable light theme.
The mark's two opposing shapes express movement between formats without encoding a fixed number
of formats or implying runtime synchronization.

Render the homepage from a dedicated Zensical template. Keep its command example in the homepage
Markdown and retain the existing documentation shell, search, header links, and legal footer.

Define currently supported formats in `project.extra.formats` in `zensical.toml`. Render one chip
and one input-guide entry per record. Both grids wrap naturally; detailed output choices remain
in the input guides. Do not publish an exhaustive route matrix or a fixed route count on the homepage.
Only add a format after its support, compatibility documentation, and input guide are published.
Planned formats and uncertain commitments do not belong in the public registry.

Map documentation link text explicitly to the accessible primary token. Keep semantic diagnostic
colors distinct from the lime brand color and verify rendered contrast in both themes.

## Consequences

- The first screen presents the action and product message without repeating a large wordmark.
- Homepage elements grow linearly with the format set and support five or six entries without a
  different template or a list of every possible route.
- Format additions still require the corresponding documentation-source and navigation updates;
  the presentation registry does not grant support or define conversion capabilities.
- Changes to the selected mark or palette regenerate the existing favicon and social-preview paths.
- Template overrides stay small and use the pinned Zensical theme's native behavior.
