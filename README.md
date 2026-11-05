# BoxFerry website

This repository builds the official [BoxFerry website](https://boxferry.dev/) for open-source,
source-aware conversion between Docker Compose, Podman resources, and Podman Quadlet, and assembles
the unified documentation below `/docs/`. The CLI, Rust library, and conversion engine live in the
[BoxFerry source repository](https://github.com/Strukturpiloten/boxferry); each technical document
remains in the repository that owns the documented behavior. This repository owns the homepage,
shared navigation, visual identity, deterministic documentation assembly, site validation, and
deployment tooling.

## Develop locally

Use the BoxFerry five-repository Dev Container workspace, then run:

```console
./scripts/check-all.sh
```

For an interactive preview:

```console
./scripts/serve.sh
```

Navigation and theme entry points are listed in [`docs/customization.md`](docs/customization.md).
Colors live in `content/assets/stylesheets/tokens.css`; logo sources and regeneration remain defined
in [`docs/brand.md`](docs/brand.md).

To compare validation cost, time the changed-files task on a prose-only edit and the complete gate
on a full-impact edit in the same environment. Record the revision, selected profile, cold and warm
wall time, user CPU time, and peak resident memory without deleting shared caches. For a hosted
pull request, record the start and completion of its validation-plan, quality, and aggregate-gate
jobs; the first start through the aggregate gate's completion is the critical path. Keep the
complete main and release validation evidence separate from this contributor-feedback comparison.

## Deploy to production

After its validation gate passes, push-triggered `CI` on `main` calls the reusable
`Production deployment` workflow automatically.
Only the exact tested revision can publish, and superseded automatic revisions are skipped. The
deployment workflow rebuilds and validates the locked site before entering the protected GitHub
`production` environment. Manual deploy, bootstrap, rollback and key-rendering operations remain
available. New servers still require administrator preparation and a manual bootstrap. Production
keeps five rollback targets.

Renovate polls the `main` branch of BoxFerry and every Lens repository. It groups changed revision
pins into one pull request and merges that pull request only after the website checks pass.

Follow the concise [`docs/deployment.md`](docs/deployment.md) runbook. It covers GitHub variables
and secrets, SSH key creation, the local server-preparation script, first publication, normal
deployment, verification, key rotation, and rollback.

The supported toolchain and repository architecture are documented in
[`docs/development.md`](docs/development.md) and [`docs/architecture.md`](docs/architecture.md).
AI-readable documentation routes and optional consumer registration are described in
[`docs/ai-documentation.md`](docs/ai-documentation.md).

## Status

The site assembles concise BoxFerry, ComposeLens, PodmanLens, and QuadletLens documentation,
checks published CLI examples, generates stable diagnostic-rule pages, and publishes first-party
Lens Rust API documentation. Successful main validation starts automatic publication of exact
locked revisions as immutable, rollback-capable static releases to Hetzner.
