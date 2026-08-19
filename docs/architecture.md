# Website architecture

The public result is one static Zensical site assembled from several independently maintained
repositories.

## Ownership

The website repository owns presentation, shared navigation, design tokens, source assembly, site
validation, and deployment. Product and library repositories own the technical Markdown that
describes their behavior. The source manifest maps accepted documents into stable public routes.

Primary BoxFerry pages come from `boxferry/docs/public/`. Its
`docs/documentation-examples.toml` file is an assembly-only contract: BoxFerry executes every
command, and the website rejects missing or changed command blocks. The manifest is removed before
the Zensical build.

## Build boundary

`scripts/assemble_docs.py` copies website-owned content into an ignored staging directory, validates
every source mapping, and records the exact pinned revisions without exposing local paths. Zensical
then turns that staging tree into the ignored `site/` directory.

After the strict Zensical build, `scripts/build_rustdoc.py` runs `cargo doc --locked --no-deps`
against the same declared Lens sources. It copies each complete Rustdoc tree below its stable
`/docs/api/<library>/` route and adds a small redirect to the generated crate index. Local mode uses
the sibling checkout; locked mode verifies and reuses the exact checkout acquired during assembly.
Generated Rustdoc remains ignored and is never copied back into a Lens repository.

The brand build is deliberately smaller than the documentation assembler. Monochrome SVG originals
and the design-token stylesheet are versioned sources. `scripts/generate_brand_assets.py` derives
the committed dark, light, favicon, and social-preview variants and fails in check mode when any
variant is missing or stale.

Small Zensical partial overrides own the shared header and footer integrations. They add local,
passive GitHub and Strukturpiloten marks, English website-owned legal pages, and a first-party
company contact link without loading remote images, scripts, fonts, or tracking resources. The
Strukturpiloten rocket is a monochrome vector reconstruction of the company favicon and inherits
the active color scheme.

The diagnostic catalogue comes from BoxFerry as checked JSON. Assembly generates one short
Markdown page per rule and the rule index. Repetitive reference text therefore cannot drift from
`boxferry rules`.

Local preview mode selects an explicitly declared sibling-checkout location so documentation
authors can preview uncommitted work on the host or in the shared Dev Container. Locked mode
obtains exact source revisions and is the only mode permitted for production builds.

## Public contract

- The canonical origin is `https://boxferry.dev/`.
- Product documentation starts at `/docs/`.
- Library documentation is secondary and starts below `/docs/libraries/`.
- Generated API documentation starts below `/docs/api/`.
- Every rule has a stable `/docs/reference/diagnostics/rules/CODE/` page.
- Site output is static and does not require application code on the webserver.
- Brand assets require no remote font, browser script, or runtime color transformation.
- Company and legal links remain visible on every generated page.

## Security and privacy

Mappings reject absolute paths, parent traversal, symlinks, duplicate destinations, and unknown
repositories. Generated metadata contains repository URLs and pinned revisions only. It never
contains checkout paths, environment values, credentials, or source-control authentication.

Public BoxFerry pages also pass a small content contract: one level-one heading, no placeholder
copy, at most 900 words per page, and no prose paragraph above 120 words. Each Lens repository
enforces a smaller exact public-page inventory before the website can assemble it. These limits
prevent reference dumps and generated filler; they are not targets to fill.
