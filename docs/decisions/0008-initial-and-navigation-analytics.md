# 0008: Automatic initial and manual navigation Analytics views

- Status: Accepted
- Date: 2026-11-05
- Amends: initial page-view ownership in [0007](0007-opt-in-analytics.md)

## Context

The maintainer confirmed destination Enhanced Measurement, Google Signals, advertising
personalization and optional Google-products sharing are off. Property-level user-provided data
collection is also off. They explicitly keep detailed location/device reporting and Google tag
automatic-detection and user-provided-data capabilities enabled. Tag capabilities and destination
collection controls have different scopes; capability flags alone do not prove transmission.
[Google documents the tag controls](https://support.google.com/analytics/answer/12131703?hl=en)
and the [initial versus history page-view controls](https://developers.google.com/analytics/devguides/collection/ga4/views).

Real Firefox testing found that a manual initial view with `send_page_view: false` was followed
about five seconds later by a second Google-generated initial view. Changing the consent-command
sequence did not remove it. Pure automatic tracking produced one initial view but no views for
completed instant navigation while destination Enhanced Measurement remained off.

## Decision

After valid current opt-in, retain all existing origin, storage, lifetime and advertising-denial
gates. Set sanitized initial page fields before configuring the property with
`send_page_view: true`. Let Google send that initial view, with no manual initial event. Send
manual views only for later completed native document navigation, deduplicated by clean canonical
path. Keep destination Enhanced Measurement off; do not disable the maintainer's tag capabilities.

Retain query/fragment removal, origin-only initial referrer, authored titles, subsequent clean
canonical referrers and immediate withdrawal. A fresh policy version requires a new explicit
choice for the clarified city/device and tag-capability notice. Describe the actual enabled
settings without claiming that all automatic capability flags imply collection.

Require settled real-browser network evidence for initial and virtual views, query/hash-only
changes, the form probe, prior-version consent, withdrawal and local preview. Preserve the
mutable-service integrity exception, pinned tooling and native Zensical UI from ADR 0007. No new
browser package, website dependency or Renovate extraction path is introduced.

## Consequences

- Each published route has one page-view owner: initial configuration or later navigation.
- The native banner remains unchecked by default and rejects without Google requests.
- Detailed data and tag settings stay at the maintainer's chosen values.
- Unit and rendered checks remain necessary; only real network tests establish current SDK behavior.
- Google service changes and account changes require renewed behavior review, not a legal-compliance claim.
