# Analytics and consent

BoxFerry uses Zensical's native consent form, not a separate banner package. The Google provider
partial loads a local adapter; the Google tag can load only after opt-in on `https://boxferry.dev`.
Local previews and other origins never load it. The footer's **Privacy settings** link reopens
the native form. Analytics is unchecked initially; **Accept** saves selected categories and
**Reject** rejects Analytics. Preferences expire after 180 days.

## Current account status

The measurement ID is `G-TX06VP39B2`. The maintainer confirmed event-data retention of **2 months**
and user-data retention of **14 months**. These differ from cookie lifetime and aggregated reports.

Collection is currently disabled by `project.extra.analytics.enabled = false` in `zensical.toml`.
The banner still appears and remembers a choice locally. Before changing the flag, confirm:

1. In the BoxFerry web stream, **Enhanced Measurement / Optimierte Analysen** is off, including
   history-based page views, search, form interactions and outbound/download events.
2. Google Signals, advertising personalization and optional Google-products-and-services sharing
   are disabled. Review connected advertising products and user-provided data collection.
3. The applicable Google data-processing terms are accepted and the privacy notice matches the
   actual account settings and transfer safeguards. Keep the separate Hetzner checks in
   [legal-maintenance.md](legal-maintenance.md).

`send_page_view: false` disables the tag's automatic configuration view; it does not independently
disable Enhanced Measurement's history-triggered views. Account confirmation is required. Do not
paste a `gtm.js` snippet into the site: this integration uses GA4's `/gtag/js` endpoint.

## Implementation and review

- Configuration: `zensical.toml`; native consent markup comes from locked Zensical.
- Provider override: `overrides/partials/integrations/analytics/google.html`.
- Lifecycle: `content/assets/javascripts/analytics.js`. Native choice storage is `__consent`;
  `__bf_analytics_consent` holds only policy version and saved/expiry timestamps. Zensical scopes
  both names by the site path. A transient boolean probe checks storage before collection.
- Privacy notice: `content/privacy-policy/index.md`; narrow CSP: `deployment/apache/.htaccess`.
- Policy and mutable-service integrity exception: [ADR 0007](decisions/0007-opt-in-analytics.md).

The adapter uses completed `document$` navigation, deduplicates query/fragment-only changes, and
strips queries/fragments from canonical page addresses. It sends no search/form contents and no
measurement or consent ping while denied. Withdrawal disables future events synchronously and
clears accessible GA cookies; it does not erase Google's existing records.

If saving a choice fails, the current page stops collection and dismisses the native overlay so
browsing remains possible. The footer can reopen the same form. A choice cannot be remembered
while browser storage refuses writes.

Run the complete gate after changes. Node lifecycle tests exercise first visit, rejection,
acceptance/reload, blocked storage, invalid/expired choices, cross-tab withdrawal, cookie cleanup
and instant navigation. Static validation checks rendered native forms and the first-party loader.
On the deployed site, also inspect browser storage and network for these cases; source/VM tests
do not execute the remote Google service. Raw Rustdoc routes have neither banner nor collection.

## References

- [Zensical consent](https://zensical.org/docs/setup/data-privacy/)
- [Google page-view configuration](https://developers.google.com/analytics/devguides/collection/ga4/views)
- [Google Analytics cookie settings](https://support.google.com/analytics/answer/11397207?hl=en)
