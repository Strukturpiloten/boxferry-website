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

Local preview mode selects an explicitly declared sibling-checkout location so documentation
authors can preview uncommitted work on the host or in the shared Dev Container. Locked mode
obtains exact source revisions and is the only mode permitted for production builds.

## Public contract

- The canonical origin is `https://boxferry.dev/`.
- Product documentation starts at `/docs/`.
- Library documentation is secondary and starts below `/docs/libraries/`.
- Generated API documentation starts below `/docs/api/`.
- Site output is static and does not require application code on the webserver.

## Security and privacy

Mappings reject absolute paths, parent traversal, symlinks, duplicate destinations, and unknown
repositories. Generated metadata contains repository URLs and pinned revisions only. It never
contains checkout paths, environment values, credentials, or source-control authentication.
