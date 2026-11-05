# Dependency policy

Dependencies must have a direct, documented purpose and be locked to reproducible versions.

## Current direct tools

| Tool              | Authoritative pin                                 | License           | Purpose                                                                     | Decision                                                         |
| ----------------- | ------------------------------------------------- | ----------------- | --------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| Zensical          | `pyproject.toml` and `uv.lock`                    | MIT               | Static site generation, navigation, search, theming, strict link validation | Accepted while pre-1.0; exact pin and complete build required    |
| uv                | shared automation manifest and verified bootstrap | Apache-2.0 OR MIT | Python environment and lock-file management                                 | Canonical shared owner; verified archive integrity               |
| Ruff              | shared automation manifest                        | MIT               | Python formatting and linting                                               | Accepted for repository tooling only                             |
| ty                | shared automation manifest                        | MIT               | Python type checking for repository scripts and tests                       | Shared with the common Python toolchain                          |
| CSpell            | `package.json` and `package-lock.json`            | MIT               | Repository spelling validation                                              | Shared editor and deterministic CI configuration                 |
| Prettier          | `package.json` and `package-lock.json`            | MIT               | Markdown, JSON, YAML, CSS, and HTML formatting                              | Shared with the other BoxFerry repositories                      |
| markdownlint-cli2 | `package.json` and `package-lock.json`            | MIT               | Markdown linting                                                            | Shared with the other BoxFerry repositories                      |
| Tombi             | shared `automation/tool-artifacts.json`           | MIT               | TOML formatting and linting                                                 | Shared with the other BoxFerry repositories                      |
| shfmt             | shared `automation/tool-artifacts.json`           | BSD-3-Clause      | Shell formatting                                                            | Shared with the other BoxFerry repositories                      |
| ShellCheck        | shared `automation/tool-artifacts.json`           | GPL-3.0           | Shell linting                                                               | Shared with the other BoxFerry repositories                      |
| Hadolint          | shared `automation/tool-artifacts.json`           | GPL-3.0           | Dockerfile linting                                                          | Shared with the other BoxFerry repositories                      |
| actionlint        | shared `automation/tool-artifacts.json`           | MIT               | GitHub Actions syntax and expression linting                                | Shared with the other BoxFerry repositories                      |
| zizmor            | `pyproject.toml` and `uv.lock`                    | MIT               | GitHub Actions security audit                                               | Shared with BoxFerry's current pin                               |
| Lychee            | shared `automation/tool-artifacts.json`           | Apache-2.0 OR MIT | Offline local links and rate-limited external-link health                   | Verified Linux release archives for both supported architectures |

Zensical is an actively maintained but pre-1.0 build dependency. Configuration changes must be
reviewed against its current documentation, and Renovate updates must pass the complete site build.

The local file-tool installer delegates the website profile or Lychee-only subset to the same
immutable shared implementation. Its canonical inventory owns all six tool versions and both
Linux architecture checksums once. The common preset updates each release tag and asset digest
atomically. No local checksum pins or routine manual approvals remain. Complete CI and deployment
install to runner temporary directories. Corrupt downloads, unsafe archives, unsupported platforms
and checksum mismatches fail before installation.

Browser-side analytics, tracking, remote fonts, or third-party JavaScript require a separate
privacy and dependency decision before addition.

## Shared update policy

The immutable common preset in `.github/renovate.json` owns automatic dependency PRs, the 72-hour
third-party hold, Python package declarations and lock maintenance. Canonical uv, Ruff and ty execution lives only
in the shared implementation; the website lock contains its site and workflow-audit dependencies. Local rules own the website's native
installer, Node setup and exact documentation-source revisions once. Documentation-source updates
are first-party updates; isolated published first-party PRs and necessary transitive resolution
have no age hold. Mixed third-party changes retain the ordinary policy.

The default-branch eligibility service evaluates metadata without executing candidate code.
Candidate CI only reads the exact revision's admission evidence using the trusted base manifest's
automation revision. Main, manual validation and protected deployment remain complete. After a dependency update merges, main CI can publish the website only through the required
validation gate and the reusable publisher in [ADR 0006](decisions/0006-validated-main-publication.md).

`deployment/historical-uv.json` freezes verified uv 0.13.5 integrity for the preserved pre-adoption
rebuild path. It is historical evidence, not an active upgrade pin: no Renovate manager extracts
it. The legacy version is read from the approved source's original TOML declaration; new sources
use their own canonical shared revision. See the deployment runbook.

## Same-commit website publisher

The CI caller uses the standard `./.github/workflows/deploy.yml` reference, which GitHub resolves
at the caller's exact commit. Pinned actionlint 1.7.12 rejects the newer `$/` spelling recommended by
zizmor. One inline `self-repository` style annotation documents that compatibility boundary; the
policy test permits only this exact local workflow and rationale. External references retain full
SHA and release-tag checks. No trigger, permission or integrity audit is disabled, and no software
pin or Renovate extraction path changes. Review the annotation when the canonical tool gains `$/`
support.

## Optional Analytics exception

[ADR 0007](decisions/0007-opt-in-analytics.md) accepts Google's property-configured hosted GA4
tag after explicit consent. Google supplies neither an immutable release version nor a supported
SRI digest for this changing endpoint. This is an explicit unavailable-integrity exception, not
a checksum-pinned dependency. The maintainer owns its privacy and behavior review and can disable
collection with `project.extra.analytics.enabled`. Do not add a fabricated version or digest.

Native consent comes from the existing locked Zensical package. The small first-party lifecycle
adapter uses browser APIs and Node's built-in test runner; no package, lockfile or tool pin changes.
Existing Renovate ownership of Zensical and tooling remains unchanged. The mutable Google service
has no release extraction path or duplicate Renovate manager. Local, PR, main and deployment
validation consume the same complete script and include its lifecycle and rendered-site checks.
