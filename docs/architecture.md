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

`scripts/prepare_deployment.py` then copies the tracked Apache policy into the site root and records
the exact website revision in private and public deployment metadata. These generated files travel
with the same immutable artifact as every HTML, JavaScript, CSS, image, search, and Rustdoc file.

After rendering, `scripts/publish_ai_docs.py` derives compact LLM indexes and stable Markdown
alternatives from the same assembled, authored source tree. It adds HTML discovery links and
checks those routes against the exact staged pages before publication; Rustdoc HTML is excluded.
See [`ai-documentation.md`](ai-documentation.md) for route and size policy.

The brand build is deliberately smaller than the documentation assembler. Monochrome SVG originals
and the design-token stylesheet are versioned sources. `scripts/generate_brand_assets.py` derives
the committed dark, light, favicon, and social-preview variants and fails in check mode when any
variant is missing or stale.

Small Zensical partial overrides own the shared header and footer integrations. They add local,
passive GitHub and Strukturpiloten marks, English website-owned legal pages, and a first-party
company contact link. Native Zensical consent and a local GA4 lifecycle adapter are described in
[`analytics.md`](analytics.md). Remote fonts and images remain disabled. The
Strukturpiloten rocket is a monochrome vector reconstruction of the company favicon and inherits
the active color scheme.

The diagnostic catalogue comes from BoxFerry as checked JSON. Assembly generates one short
Markdown page per rule and the rule index. Repetitive reference text therefore cannot drift from
`boxferry rules`.

Local preview mode selects an explicitly declared sibling-checkout location so documentation
authors can preview uncommitted work on the host or in the shared Dev Container. Locked mode
obtains exact source revisions and is the only mode permitted for production builds.

Renovate polls the `main` Git ref of every declared documentation source. It groups changed commit
digests into one revision-pin pull request and enables merge only after the locked website checks
pass. The versioned manifest therefore remains the production source of truth.

## Deployment boundary

GitHub Actions builds the locked site before entering the protected `production` environment. One
forced SSH key writes only to Hetzner's unserved `incoming/` subtree through `rrsync`. A second forced
key serializes the fixed version updater with `flock`. The updater moves a validated staging tree
into immutable release storage, rotates four previous links, and changes the served `current` link
last. The updater permits one server-enforced bootstrap only while no releases exist, allowing the
first `current` link to be created before Hetzner can serve that path. Every later activation runs
HTTPS and Apache policy checks before finalization; failures restore the saved link state.

CI validation jobs check the complete locked site without production secrets. After the required
validation gate succeeds, main push CI calls the reusable `Production deployment` workflow for
that exact commit. Only its two named deployment keys are forwarded for repository-level
credential compatibility; validation steps do not receive those keys. The called production
environment can supply its own keys. Other CI contexts cannot call automatic publication, and the request selector
rejects invalid caller contexts and skips superseded automatic revisions. The publisher
checks current main again before using its artifact or SSH keys. Main CI and production remain
serialized without canceling an active publisher;
manual deploy, bootstrap, key rendering and rollback remain available. Every publication rebuilds
and validates its selected exact revision before using the protected `production` environment.

The deployment contract and administrator procedure are defined in [`deployment.md`](deployment.md)
and [decision 0003](decisions/0003-hetzner-atomic-static-deployment.md), with automatic triggering
defined by [decision 0006](decisions/0006-validated-main-publication.md).

## Public contract

- The canonical origin is `https://boxferry.dev/`.
- Product documentation starts at `/docs/`.
- Open-source and professional support starts at `/support/`.
- Exact build provenance is visible at `/docs/sources/` and in its machine-readable manifest.
- Library documentation is secondary and starts below `/docs/libraries/`.
- Generated API documentation starts below `/docs/api/`.
- Every rule has a stable `/docs/reference/diagnostics/rules/CODE/` page.
- Site output is static and does not require application code on the webserver.
- Every release carries the same generated root `.htaccess` policy and exact website revision.
- Brand assets require no remote font, browser script, or runtime color transformation.
- Company and legal links remain visible on every generated page.

## Security and privacy

Mappings reject absolute paths, parent traversal, symlinks, duplicate destinations, and unknown
repositories. Generated metadata contains repository URLs and pinned revisions only. It never
contains checkout paths, environment values, credentials, or source-control authentication.

Remote fonts remain disabled. Optional GA4 requires a current explicit opt-in, the production
origin and an enabled collection setting; no Google request precedes these gates. The native
Zensical banner owns choices, with a permanent footer settings link. A local adapter expires
preferences after 180 days, handles withdrawal and emits only query-free canonical page views.
Collection remains disabled pending confirmation of the Google account settings.

Apache denies the private release manifest and adds a content policy with narrowly scoped Google
Analytics exceptions, HSTS, framing denial, MIME protection, referrer policy, and capability
restrictions. Deployment SSH host identity is pinned, private keys remain
environment secrets, and neither forced key grants an interactive shell.

Public BoxFerry pages also pass a small content contract: one level-one heading, no placeholder
copy, at most 900 words per page, and no prose paragraph above 120 words. Each Lens repository
enforces a smaller exact public-page inventory before the website can assemble it. These limits
prevent reference dumps and generated filler; they are not targets to fill.
