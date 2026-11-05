# 0007: Native consent and optional Google Analytics

- Status: Accepted; initial page-view ownership amended by [0008](0008-initial-and-navigation-analytics.md)
- Date: 2026-11-05
- Amends: browser policy in [0003](0003-hetzner-atomic-static-deployment.md)

## Context

The maintainer requested GA4 measurement for BoxFerry and an existing consent solution. Zensical
already provides a banner, saved choices and footer settings. Its default Google integration does
not provide the required URL minimization, preference lifetime or full withdrawal lifecycle.

## Decision

Use the pinned Zensical banner, with an unchecked Analytics category, equally styled accept and
reject actions, and permanent footer access. Do not build another banner or add a consent package.
Replace only its Google provider partial with a first-party lifecycle adapter.

Before any Google request, require an explicit native Analytics opt-in, matching versioned
metadata, writable storage, the canonical production origin and an enabled collection flag.
Missing, malformed, legacy, expired or changed-policy records cannot authorize collection.
Preferences expire after 180 days and contain no separate identifier. Google cookie expiry is
180 days without renewal on visits. Withdrawal immediately disables measurements, unsubscribes
owned navigation work and removes accessible GA cookies, including across tabs. Denied consent
sends no Google tag or consent ping; use basic consent gating.

Use the correct hosted `/gtag/js` service for `G-TX06VP39B2`, never a GTM container. Deny advertising
consent and disable Google Signals and advertising personalization. Page views use same-origin
published canonical URLs without queries or fragments, authored titles and an origin-only initial
referrer. The original manual-initial-view rule is superseded by
[0008](0008-initial-and-navigation-analytics.md): Google owns the initial configuration view and
manual events own subsequent completed native navigation. Do not collect local search or
form contents. Keep Enhanced Measurement disabled in the property to avoid independent events.
No cross-domain visitor linking is configured; existing referral UTM links remain ordinary links.

Collection was held disabled until the maintainer confirmed Enhanced Measurement, Google Signals,
advertising personalization and optional Google-products sharing are off. Document Google
processing, international transfers, withdrawal and the confirmed event/user retention settings
of 2/14 months in the privacy policy. Account agreements and hosting facts still require the
maintainer's verification.

Allow only the Google tag path in `script-src` and the global and EU Analytics collection hosts
in `connect-src` and `img-src`. Preserve the other Apache restrictions. Google publishes no fixed
version or supported integrity hash for this property-configured changing tag: accept this
unavailable-integrity exception explicitly. The maintainer owns service/privacy review; existing
Renovate ownership continues for pinned Zensical and tools, with no new package or extraction.

## Consequences

- Visitors can reject Analytics without losing website functionality.
- The banner is delivered independently of the collection flag; disabled collection stays local.
- Native-template, JavaScript lifecycle and rendered-site regressions join the complete gate.
- Browser network checks and account configuration remain necessary operational evidence; tests
  do not certify GDPR compliance or prove Google's internal behavior.
- Generated raw Rustdoc pages have no Zensical banner or Analytics integration.
