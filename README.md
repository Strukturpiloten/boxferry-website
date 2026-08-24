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

## Deploy to production

Successful push-triggered CI runs on `main` automatically publish their exact revision through the
protected GitHub `production` environment. The same workflow retains manual `deploy`, `bootstrap`,
`rollback`, and key-rendering operations. New servers require one administrator preparation and
one manual `bootstrap` publication. Production keeps five rollback targets.

Renovate polls the `main` branch of BoxFerry and every Lens repository. It groups changed revision
pins into one pull request and merges that pull request only after the website checks pass.

Follow the concise [`docs/deployment.md`](docs/deployment.md) runbook. It covers GitHub variables
and secrets, SSH key creation, the local server-preparation script, first publication, normal
deployment, verification, key rotation, and rollback.

The supported toolchain and repository architecture are documented in
[`docs/development.md`](docs/development.md) and [`docs/architecture.md`](docs/architecture.md).

## Status

The site assembles concise BoxFerry, ComposeLens, PodmanLens, and QuadletLens documentation,
checks published CLI examples, generates stable diagnostic-rule pages, and publishes first-party
Lens Rust API documentation. The production workflow builds exact locked revisions and
deploys immutable, rollback-capable static releases to Hetzner automatically or on manual request.
