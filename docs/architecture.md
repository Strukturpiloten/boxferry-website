# Website architecture

The public result is one static Zensical site assembled from several independently maintained
repositories.

## Ownership

The website repository owns presentation, shared navigation, design tokens, source assembly, site
validation, and deployment. Product and library repositories own the technical Markdown that
describes their behavior. The source manifest maps accepted documents into stable public routes.

## Build boundary

`scripts/assemble_docs.py` copies website-owned content into an ignored staging directory, validates
every source mapping, and records the exact pinned revisions without exposing local paths. Zensical
then turns that staging tree into the ignored `site/` directory.

The brand build is deliberately smaller than the documentation assembler. Monochrome SVG originals
and the design-token stylesheet are versioned sources. `scripts/generate_brand_assets.py` derives
the committed dark, light, favicon, and social-preview variants and fails in check mode when any
variant is missing or stale.

Local preview mode selects an explicitly declared sibling-checkout location so documentation
authors can preview uncommitted work on the host or in the shared Dev Container. Locked mode
obtains exact source revisions and is the only mode permitted for production builds.

## Public contract

- The canonical origin is `https://boxferry.dev/`.
- Product documentation starts at `/docs/`.
- Library documentation is secondary and starts below `/docs/libraries/`.
- Generated API documentation starts below `/docs/api/`.
- Site output is static and does not require application code on the webserver.
- Brand assets require no remote font, browser script, or runtime color transformation.

## Security and privacy

Mappings reject absolute paths, parent traversal, symlinks, duplicate destinations, and unknown
repositories. Generated metadata contains repository URLs and pinned revisions only. It never
contains checkout paths, environment values, credentials, or source-control authentication.
