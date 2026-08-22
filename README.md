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

The supported toolchain and repository architecture are documented in
[`docs/development.md`](docs/development.md) and [`docs/architecture.md`](docs/architecture.md).

## Status

The site assembles concise BoxFerry, ComposeLens, PodmanLens, and QuadletLens documentation,
checks published CLI examples, generates stable diagnostic-rule pages, and publishes first-party
Lens Rust API documentation. Production deployment remains a later milestone.
