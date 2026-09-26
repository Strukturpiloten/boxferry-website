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

For quick feedback on a branch, run `./scripts/check-changes.sh` or the matching VS Code task.
It checks formatting, Markdown lint, spelling, and offline local links for a small, explicit set of
repository-maintenance documents when those are the only changes relative to `origin/main`. Pass another trusted base ref
as the first argument for a stacked branch. Untracked files, renamed or deleted files, site content,
assets, source pins, workflow files, dependencies, scripts, and uncertain comparisons use the
complete check. This quick task is development feedback; it does not replace the required complete
local gate before publishing a PR.

On GitHub, a pull request uses its trusted base revision to choose the same maintenance profile.
The stable `Format, lint, test, and build` check runs the selected validation steps, and the `PR gate`
requires the plan and check to succeed. A policy
change itself runs full validation. Main branch pushes and manually dispatched CI always run the
complete locked-source check. The production deployment workflow still builds and validates the
exact selected revision before accessing the protected environment. The website's Markdown under
`content/` is site input and always requires full validation.

The maintenance job downloads only a checksum-verified Lychee binary into its runner temporary
directory instead of compiling it with Cargo. A local warm run with an already installed Lychee
took about 2.4 seconds; this does not include GitHub runner startup or a cold archive download.
One isolated unprivileged download and install took 0.8 seconds on the development host. Hosted
timing remains to be measured.

Run the same complete task required before a pull request:

```console
./scripts/check-all.sh
```

The task formats owned files, checks spelling, validates every supported file type, runs Python
tests, regenerates token-derived brand assets, assembles the documentation, performs a strict
Zensical build, generates first-party Lens Rustdoc and authored Markdown alternatives, checks
required public routes and assets, and
prepares the Apache deployment artifact, validates its privacy and server-policy boundaries, and
checks local links without contacting external web servers.

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

Use [`customization.md`](customization.md) for the exact navigation, content-width, color-token, and
logo entry points.

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
uv run --frozen python scripts/publish_ai_docs.py
uv run --frozen python scripts/prepare_deployment.py
```

Locked assembly may access GitHub to obtain exact revisions declared in
`documentation-sources.toml`. Normal local validation uses sibling checkouts and does not download
documentation sources. Rustdoc reuses the same local or revision-verified source selected for the
Markdown build.

## Agent-assisted verification

Repository model defaults and role overrides live in [`.codex/`](../.codex/); permissions and
workflow ownership remain defined in [`AGENTS.md`](../AGENTS.md). Reload or start a new trusted
project session after updating configuration; an explicit session override can take precedence.
Keep any explicit primary-session override aligned with Sol/xhigh.

Use `./scripts/check-all.sh --check` to run the complete gate without formatting repository-owned
files. The default command (or `--fix`) still formats first. Both modes run the same validation;
ignored caches and build artifacts may change. Verifiers report failures without fixing files,
and the primary agent owns the final complete gate and merges covered by the workspace standing authorization in `AGENTS.md`.
