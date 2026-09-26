# Dependency policy

Dependencies must have a direct, documented purpose and be locked to reproducible versions.

## Current direct tools

| Tool              | Authoritative pin                              | License           | Purpose                                                                     | Decision                                                         |
| ----------------- | ---------------------------------------------- | ----------------- | --------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| Zensical          | `pyproject.toml` and `uv.lock`                 | MIT               | Static site generation, navigation, search, theming, strict link validation | Accepted while pre-1.0; exact pin and Renovate review required   |
| uv                | `pyproject.toml` and workflow `version` inputs | Apache-2.0 OR MIT | Python environment and lock-file management                                 | Accepted; exact tool requirement and immutable container image   |
| Ruff              | `pyproject.toml` and `uv.lock`                 | MIT               | Python formatting and linting                                               | Accepted for repository tooling only                             |
| CSpell            | `package.json` and `package-lock.json`         | MIT               | Repository spelling validation                                              | Shared editor and deterministic CI configuration                 |
| Prettier          | `package.json` and `package-lock.json`         | MIT               | Markdown, JSON, YAML, CSS, and HTML formatting                              | Shared with the other BoxFerry repositories                      |
| markdownlint-cli2 | `package.json` and `package-lock.json`         | MIT               | Markdown linting                                                            | Shared with the other BoxFerry repositories                      |
| Tombi             | `scripts/install-file-tools.sh`                | MIT               | TOML formatting and linting                                                 | Shared with the other BoxFerry repositories                      |
| shfmt             | `scripts/install-file-tools.sh`                | BSD-3-Clause      | Shell formatting                                                            | Shared with the other BoxFerry repositories                      |
| ShellCheck        | `scripts/install-file-tools.sh`                | GPL-3.0           | Shell linting                                                               | Shared with the other BoxFerry repositories                      |
| Hadolint          | `scripts/install-file-tools.sh`                | GPL-3.0           | Dockerfile linting                                                          | Shared with the other BoxFerry repositories                      |
| actionlint        | `scripts/install-file-tools.sh`                | MIT               | GitHub Actions syntax and expression linting                                | Shared with the other BoxFerry repositories                      |
| zizmor            | `pyproject.toml` and `uv.lock`                 | MIT               | GitHub Actions security audit                                               | Shared with BoxFerry's current pin                               |
| Lychee            | `scripts/install-file-tools.sh`                | Apache-2.0 OR MIT | Offline local links and rate-limited external-link health                   | Verified Linux release archives for both supported architectures |

Zensical is an actively maintained but pre-1.0 build dependency. Configuration changes must be
reviewed against its current documentation, and Renovate updates must pass the complete site build.

The file-tool installer verifies the versioned Lychee archive against a recorded SHA-256 for each
Linux architecture and checks the extracted executable's version. Its `--lychee-only` mode keeps
repository-maintenance PRs from downloading the other native tools. Renovate tracks the upstream
`lychee-v` release tags at the installer pin and requires approval and fresh checksum review for
both archives before an update can merge. The full installer remains the canonical tool setup for
complete CI and deployment checks. GitHub jobs install these tools without `sudo` into their own
runner temporary directory and add only that directory to the job's executable path.

Browser-side analytics, tracking, remote fonts, or third-party JavaScript require a separate
privacy and dependency decision before addition.
