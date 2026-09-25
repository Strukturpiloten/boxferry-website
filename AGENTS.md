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

## Workspace scope and standing GitHub authorization

The maintainer grants standing authorization for task-related Git and GitHub work only in these
workspace repositories:

- `Strukturpiloten/boxferry`
- `Strukturpiloten/compose-lens`
- `Strukturpiloten/podman-lens`
- `Strukturpiloten/quadlet-lens`
- `Strukturpiloten/boxferry-website`
- `Strukturpiloten/docker-lens`

Do not work on or modify any repository outside this explicit allowlist, including its issues,
pull requests, branches, settings, or workflows. An upstream documentation reference is not
permission to operate on that upstream repository. A newly discovered checkout is not implicitly
in scope.

For user-requested work within this scope, the primary agent may create issues, branches, commits,
pushes, and pull requests and merge verified task-related pull requests without asking for renewed
approval. This permission does not authorize unrelated backlog work, implementation of
discussion-only proposals, or expansion of the requested product scope. A later user instruction
may narrow or revoke this permission.

Immediately before merging, read back the exact head commit and verify that the pull request is
ready, mergeable, independently reviewed, and has every required check successful. Use the normal
merge method with an exact-head safeguard; never bypass branch protection or use an administrator
override. Read back the merged state and merge commit, synchronize local `main` with `origin/main`,
and remove the task's recorded worktrees and verified merged local branches while preserving
unrelated work.

This standing permission does not authorize releases, publication, deployment operations, or
merging release/publication/deployment pull requests; those require a separate explicit request.
The primary agent owns all Git and GitHub writes. Subagents remain within their assigned task and
checkout and must not perform those writes.

The primary agent owns Git and GitHub writes, final integration, complete local validation, and
the final diff review. Subagents never commit, push, publish, tag, release, or deploy the site.

## Agent roles and verification

Model defaults belong in [`.codex/config.toml`](.codex/config.toml); task-specific models and
reasoning belong in [`.codex/agents/`](.codex/agents/). The primary manager always uses
`gpt-6-astra` with `xhigh` reasoning. Implementation, specification research, and independent review
use `gpt-6-sol` with `high` reasoning; check-only verification uses `gpt-6-luna` with `high`
reasoning. Use Luna for bounded read-only exploration and Sol for difficult failure diagnosis.
These model settings do not expand the workspace scope or grant additional permissions.

- Delegate bounded tasks when independent work can usefully proceed in parallel. Define the shared
  contract and explicit repository, checkout, and file ownership before delegation.
- Use up to nine concurrent subagents plus the primary manager, subject to the session's actual
  runtime limit. Nine is a ceiling, not a target or nine distinct roles: several subagents may use
  the same role for independent tasks. Do not create nested agents to evade the limit.
- Never run two writers in one checkout. Use separate assigned repositories or worktrees for
  concurrent implementation. Research and review remain read-only.
- The reviewer checks the original requirements and independent expected results, not just agreement
  between the implementation and its tests.
- After writing finishes, the verifier runs `./scripts/check-all.sh --check`. It reports failures
  without formatting or editing tracked files; ignored build artifacts and caches are allowed.
- Run at most one complete gate or heavy runtime suite at a time across this workspace. Agent
  concurrency is not permission for competing builds. The primary owns integration, the final
  complete gate, and every authorized Git or GitHub write.

The default `./scripts/check-all.sh` still formats before checking. `--check` runs the same
complete gate without source formatting; it is not a reduced test tier. A later edit invalidates
either result. Neither mode grants release, publication, or deployment authority.

## Cross-repository workflow version policy

- Keep equivalent local development tasks, GitHub PR, main, and release workflow definitions aligned across BoxFerry, ComposeLens, PodmanLens, QuadletLens, DockerLens, and the website where responsibilities match. Before a change, identify the canonical definition and every affected consumer; coordinate updates and document justified repository-specific differences.
- Reuse common scripts, actions, and workflows without making Lens product libraries depend on BoxFerry. Preserve native conformance, least privilege, exact-candidate evidence, resource budgets, and cleanup. One repository passing does not establish that a shared rollout is complete.
- Every added or changed software dependency or operational tool/runtime pin needs an explicit version and immutable integrity information where the ecosystem supports it:
  - Container images: readable version tag plus immutable digest.
  - GitHub Actions and reusable workflows: full commit SHA plus exact release-tag comment.
  - Downloaded tools: version plus verified checksum for the selected artifact.
  - Package dependencies: policy-compliant version declarations, lock files, and integrity records.
    Document justified exceptions when integrity metadata is unavailable; never invent a checksum, replace a reviewed pin with a floating reference, or weaken existing admission controls.
- Whenever a pin or definition is added, changed, moved, or removed, review Renovate in the same change: canonical ownership, manager paths, extraction, grouping, approvals, and regression coverage. Update configuration and affected consumers together. If no configuration edit is needed, record verified extraction evidence and the reason in the issue or PR. Avoid duplicate managers for the same operational pin; keep historical evidence and intentional fixtures outside automatic update streams.
- These rules do not change current validation gates or grant release, publication, deployment, or out-of-workspace authority. Agent model choices remain maintainer-owned routing policy, not automatically updated software dependencies.

## Code discovery

For code discovery, use an available codebase-memory graph first; otherwise use CodeGraph only if
the repository already has a usable index. Do not create an index without user authorization.
If neither graph is available or a query cannot answer the question, use `rg` and targeted reads.
For string literals, configuration, scripts, and documentation, start with `rg` directly.

## After an authorized merge

Read back the merged state and exact merge commit, then synchronize the primary checkout with
`origin/main`. Preserve unrelated files. Remove only the recorded task worktree with
`git worktree remove <recorded-path>`, delete the verified merged local issue branch with
`git branch --delete --force TheRealBecks/issue<NUMBER>`, and run
`git worktree prune --verbose`. Read back `git worktree list --porcelain` and
`git status --short --branch`; do not leave stale task worktree registrations.
