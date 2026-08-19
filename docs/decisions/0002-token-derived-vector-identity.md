# 0002: Token-derived vector identity

- Status: Accepted
- Date: 2026-08-19

## Context

BoxFerry needs a recognizable product identity for a dark-first website, documentation navigation,
favicons, and social previews. Literal colors must remain centralized, remote fonts are outside the
privacy boundary, and this community-scale project should not require a complex design build.

Three vector directions were evaluated: a cargo route, a ferry wake, and a BF monogram. The cargo
route most clearly represents N:N conversion while remaining recognizable at navigation and
favicon sizes.

## Decision

Use the cargo-route mark as the BoxFerry identity. Keep compact-mark and wordmark originals as
monochrome SVG files using `currentColor`. Generate dark, light, favicon, and social-preview SVG
variants deterministically from the literal colors in `content/assets/stylesheets/tokens.css`.

Commit generated variants for direct static-site and external use. The complete repository gate
must reject missing or stale variants. Tests must verify asset safety, centralized color ownership,
documented contrast thresholds, reduced-motion support, and stable public asset paths.

Use local system-font stacks. Do not add a remote font, analytics, tracking, or a third-party
browser dependency as part of the identity.

## Consequences

- A brand-color change happens in one source file and requires deterministic regeneration.
- The static site can serve complete SVG assets without a client-side generation step.
- Monochrome originals remain usable where application-specific colors are required.
- Generated assets contain literal colors by design, but tests prove those values come from the
  central token source.
- A future identity change must supersede this decision and preserve stable asset redirects or
  document an intentional break.
