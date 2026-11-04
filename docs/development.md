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

For change-aware feedback, run `./scripts/check-changes.sh` or the matching VS Code task. It
uses the immutable shared launcher and `scripts/validation-policy.json`. Known maintenance prose
gets formatting, spelling and offline links. Website-owned public Markdown gets those checks,
safe documentation assembly, a clean strict Zensical build and authored Markdown-route checks.
The public-prose task does not build Rust API artifacts. Mixed source/configuration changes and
unknown or unsafe comparisons run the complete gate. Pass another trusted base ref as the first
argument for a stacked branch.

Pull requests and merge queues use policy from their exact trusted base. The stable `Required CI`
check independently verifies the plan and selected job outcomes. Main pushes and manually
dispatched CI always run the complete locked-source check. The complete gate remains mandatory
before PR publication; targeted feedback does not replace it.

`.github/automation.json`, shared workflow references and the common Renovate preset select one
immutable BoxFerry automation revision. Adoption first installs the complete-only manifest, policy
and trusted service. A subsequent change enables shared planning and admission. Rollback restores
the previous reviewed revision in all three locations. The production workflow still validates
the exact selected revision before entering its protected environment.

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

The shared preview task has a two-hour watchdog; restart it when needed.

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

With Node.js 22 or newer, Git and Python installed, the verified launcher supplies canonical
uv, Ruff and ty. For the complete build:

```console
./scripts/check-all.sh --check
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
