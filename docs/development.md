# Development

## Supported environment

The preferred environment is the BoxFerry five-repository Dev Container workspace. It provides the
same pinned file-quality tools used by BoxFerry, ComposeLens, PodmanLens, and QuadletLens, plus
`uv` for the Zensical and Python toolchain.

The sibling checkouts must share one parent directory:

```text
boxferry/
boxferry-website/
compose-lens/
podman-lens/
quadlet-lens/
```

## Complete local validation

Run the same complete task required before a pull request:

```console
./scripts/check-all.sh
```

The task formats owned files, checks spelling, validates every supported file type, runs Python
tests, regenerates token-derived brand assets, assembles the documentation, performs a strict
Zensical build, generates first-party Lens Rustdoc, checks required public routes and assets, and
validates local links without contacting external web servers.

Brand direction, asset inventory, accessibility targets, and regeneration details are documented
in [`brand.md`](brand.md).

## Preview

Start a local preview after assembling content from the sibling repositories:

```console
./scripts/serve.sh
```

Open `http://localhost:8000/`. The preview is a complete static build, including the generated Lens
Rust API pages.

The temporary documentation plan under `temp/` is deliberately excluded from Git and from the
public build.

## Author documentation

Read [`content-guidelines.md`](content-guidelines.md) before adding a public page. Technical text
and executable examples stay in the repository that owns the behavior. The website owns assembly,
shared navigation, presentation, and generated rule pages.

After changing a displayed BoxFerry command, update its entry in
`boxferry/docs/documentation-examples.toml` and run BoxFerry's complete gate before updating the
website revision pin.

## Clean checkout

With Node.js 22 or newer and uv 0.12.5 installed:

```console
npm ci --ignore-scripts
uv sync --locked
uv run --frozen python scripts/assemble_docs.py --source-mode locked
uv run --frozen zensical build --strict
uv run --frozen python scripts/build_rustdoc.py --source-mode locked
```

Locked assembly may access GitHub to obtain exact revisions declared in
`documentation-sources.toml`. Normal local validation uses sibling checkouts and does not download
documentation sources. Rustdoc reuses the same local or revision-verified source selected for the
Markdown build.
