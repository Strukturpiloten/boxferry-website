# Repository guidance for coding agents

This file applies to the entire BoxFerry website repository.

## Read before changing the site

Read these documents in order:

1. `README.md`
2. `docs/architecture.md`
3. `docs/development.md`
4. `docs/dependency-policy.md`
5. `docs/decisions/README.md` and all accepted decisions

If a change contradicts an accepted decision, update or supersede it in the same change.

## Repository boundaries

- This repository owns the BoxFerry product homepage, shared documentation navigation, search,
  visual identity, documentation assembly, site validation, and deployment.
- BoxFerry user, CLI, conversion, diagnostic, privacy, architecture, and contributor documentation
  belongs in the `boxferry` repository.
- Format-specific library documentation belongs in the corresponding ComposeLens, PodmanLens, or
  QuadletLens repository.
- Do not duplicate technical Markdown from another repository. Add an explicit source mapping to
  `documentation-sources.toml` after the source document has been rewritten and accepted.
- Generated content under `.generated/` and static output under `site/` must never be committed.
- Do not add analytics, tracking, remote fonts, or third-party browser scripts without an accepted
  privacy and dependency decision.

## Non-negotiable behavior

- Keep `https://boxferry.dev/` canonical and the unified documentation below `/docs/`.
- A production build uses only exact repository revisions from `documentation-sources.toml`.
- Reject absolute, parent-traversing, duplicate, or symlinked source mappings.
- Never include secrets, raw environments, private runtime data, or host paths in site artifacts,
  fixtures, diagnostics, or snapshots.
- Keep all literal color values in `content/assets/stylesheets/tokens.css`.
- Default to dark mode while retaining a user-selectable light mode.
- Treat Zensical warnings as build failures.
- Start every repository-owned complete YAML document with `---`.
- Pin every GitHub Action to its full commit SHA and append its exact release tag as a comment.

## Canonical development commands

```shell
./scripts/check-all.sh
./scripts/serve.sh
uv run --frozen python scripts/assemble_docs.py --source-mode local
uv run --frozen zensical build --strict
```

The complete check formats owned files before validating them. Any source, test, configuration, or
documentation change after a successful run invalidates that result and requires another complete
run.

## Testing requirements

- Add positive and negative unit tests for documentation-assembly behavior.
- Test path traversal, symlinks, duplicate destinations, invalid manifests, and revision handling.
- Keep documented commands executable and validate generated public routes.
- Validate source Markdown and the generated static site without external-network dependency.

## GitHub issue-to-PR workflow

When the user authorizes the full Git workflow:

1. Inspect the status and complete diff; preserve unrelated changes.
2. Search for a duplicate issue and create a focused issue when none exists.
3. Fetch `origin/main`, synchronize local `main`, and create `TheRealBecks/issue<NUMBER>`.
4. Run `./scripts/check-all.sh`; a failure is a hard gate against commit, push, and PR creation.
5. Stage only explicit in-scope paths, run `git diff --cached --check`, and review the staged diff.
6. Use a non-release Conventional Commit type for documentation, tests, CI, build tooling, and
   repository maintenance.
7. Push the issue branch and open a ready-for-review PR containing `Closes #<NUMBER>`.
8. Read back and report the issue, branch, commit, validation, PR URL, and check state.

Opening and reading back the ready pull request is the default stopping point. Authorization to run
the Git workflow or perform GitHub writes does not authorize a merge.

Merge only when the user explicitly authorizes merging the specific pull request or the scoped set
of pull requests in the current request. Immediately before merging, read back the exact head
commit and verify that the pull request is ready, mergeable, and has every required check
successful. Never bypass branch protection, use an administrator override, or infer authority for
an out-of-scope release, publication, or deployment pull request.

Use the repository's normal merge method with an exact-head safeguard, then read back and report
the merged state and merge commit.

The primary Sol agent owns Git and GitHub writes, final integration, complete local validation, and
the final diff review. Subagents never commit, push, publish, tag, release, or deploy the site.
