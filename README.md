# BoxFerry website

This repository builds the product website at [boxferry.dev](https://boxferry.dev/) and assembles
the unified BoxFerry documentation below `/docs/`.

Technical documentation remains in the repository that owns the documented behavior. This
repository owns the homepage, shared navigation, visual identity, deterministic documentation
assembly, site validation, and deployment tooling.

## Develop locally

Use the BoxFerry five-repository Dev Container workspace, then run:

```console
./scripts/check-all.sh
```

For an interactive preview:

```console
./scripts/serve.sh
```

The supported toolchain, repository architecture, and production runbook are documented in
[`docs/development.md`](docs/development.md), [`docs/architecture.md`](docs/architecture.md), and
[`docs/deployment.md`](docs/deployment.md).

## Status

The site assembles concise BoxFerry, ComposeLens, PodmanLens, and QuadletLens documentation,
checks published CLI examples, generates stable diagnostic-rule pages, and publishes first-party
Lens Rust API documentation. The manual production workflow builds exact locked revisions and
deploys immutable, rollback-capable static releases to Hetzner after environment approval.
