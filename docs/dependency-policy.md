# Dependency policy

Dependencies must have a direct, documented purpose and be locked to reproducible versions.

## Current direct tools

| Tool              | Version | License           | Purpose                                                                     | Decision                                                       |
| ----------------- | ------- | ----------------- | --------------------------------------------------------------------------- | -------------------------------------------------------------- |
| Zensical          | 0.0.56  | MIT               | Static site generation, navigation, search, theming, strict link validation | Accepted while pre-1.0; exact pin and Renovate review required |
| uv                | 0.12.5  | Apache-2.0 OR MIT | Python environment and lock-file management                                 | Accepted; exact tool requirement and immutable container image |
| Ruff              | 0.16.3  | MIT               | Python formatting and linting                                               | Accepted for repository tooling only                           |
| CSpell            | 10.0.1  | MIT               | Repository spelling validation                                              | Shared editor and deterministic CI configuration               |
| Prettier          | 3.9.6   | MIT               | Markdown, JSON, YAML, CSS, and HTML formatting                              | Shared with the other BoxFerry repositories                    |
| markdownlint-cli2 | 0.23.2  | MIT               | Markdown linting                                                            | Shared with the other BoxFerry repositories                    |
| Tombi             | 1.4.0   | MIT               | TOML formatting and linting                                                 | Shared with the other BoxFerry repositories                    |
| shfmt             | 3.13.1  | BSD-3-Clause      | Shell formatting                                                            | Shared with the other BoxFerry repositories                    |
| ShellCheck        | 0.11.0  | GPL-3.0           | Shell linting                                                               | Shared with the other BoxFerry repositories                    |
| Hadolint          | 2.15.1  | GPL-3.0           | Dockerfile linting                                                          | Shared with the other BoxFerry repositories                    |
| actionlint        | 1.7.12  | MIT               | GitHub Actions syntax and expression linting                                | Shared with the other BoxFerry repositories                    |
| zizmor            | 1.28.0  | MIT               | GitHub Actions security audit                                               | Shared with BoxFerry's current pin                             |
| Lychee            | 0.24.2  | Apache-2.0 OR MIT | Offline local links and rate-limited external-link health                   | Shared with the other BoxFerry repositories                    |

Zensical is an actively maintained but pre-1.0 build dependency. Configuration changes must be
reviewed against its current documentation, and Renovate updates must pass the complete site build.

Browser-side analytics, tracking, remote fonts, or third-party JavaScript require a separate
privacy and dependency decision before addition.
