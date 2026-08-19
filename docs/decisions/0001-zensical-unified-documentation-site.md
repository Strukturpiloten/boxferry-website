# 0001: Zensical unified documentation site and repository ownership

- Status: Accepted
- Date: 2026-08-19

## Context

BoxFerry needs a polished product homepage, one human- and machine-consumable documentation site,
secondary documentation for multiple Lens libraries, centralized branding, and deployment to an
ordinary Hetzner webserver. Technical documentation must evolve with the code that defines it
without being copied into a central repository.

## Decision

Use Zensical to build one static site at `https://boxferry.dev/`, with unified documentation below
`/docs/`. Keep technical Markdown in BoxFerry and the Lens repositories. Assemble only explicit
documents from exact revisions declared in a versioned manifest.

The website repository owns the homepage, shared pages, navigation, visual identity, assembly,
validation, and deployment. Dark mode is the first-visit default, light mode remains selectable,
and literal colors are centralized in one token stylesheet.

Zensical is pinned exactly while it remains pre-1.0. Production builds use locked source mode and
strict validation. Deployment will upload versioned static releases and atomically change a server
symlink; deployment itself is a later milestone.

## Consequences

- Users receive one search and navigation experience instead of separate public documentation
  sites.
- Library maintainers edit technical documentation next to their implementation.
- The website build must verify revision pins, path safety, local links, and stable public routes.
- A clean build may fetch exact public Git revisions, while normal local validation remains
  network-independent by using sibling checkouts.
- Zensical upgrades require deliberate configuration and rendered-output review.
