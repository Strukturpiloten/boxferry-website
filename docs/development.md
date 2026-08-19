# Development

## Supported environment

The preferred environment is the BoxFerry four-repository Dev Container workspace. It provides the
same pinned file-quality tools used by BoxFerry, ComposeLens, and QuadletLens, plus `uv` for the
Zensical and Python toolchain.

The sibling checkouts must share one parent directory:

```text
boxferry/
boxferry-website/
compose-lens/
quadlet-lens/
```

## Complete local validation

Run the same complete task required before a pull request:

```console
./scripts/check-all.sh
```

The task formats owned files, checks spelling, validates every supported file type, runs Python
tests, regenerates token-derived brand assets, assembles the documentation, performs a strict
Zensical build, checks required public routes and assets, and validates local links without
contacting external web servers.

Brand direction, asset inventory, accessibility targets, and regeneration details are documented
in [`brand.md`](brand.md).

## Preview

Start a local preview after assembling content from the sibling repositories:

```console
./scripts/serve.sh
```

The temporary documentation plan under `temp/` is deliberately excluded from Git and from the
public build.

## Clean checkout

With Node.js 22 or newer and uv 0.12.5 installed:

```console
npm ci --ignore-scripts
uv sync --locked
uv run --frozen python scripts/assemble_docs.py --source-mode locked
uv run --frozen zensical build --strict
```

Locked assembly may access GitHub to obtain exact revisions declared in
`documentation-sources.toml`. Normal local validation uses sibling checkouts and does not download
documentation sources.
