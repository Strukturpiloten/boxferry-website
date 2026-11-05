# Analytics and consent

BoxFerry uses Zensical's native consent form, not a separate banner package. The Google provider
partial loads a local adapter; the Google tag can load only after opt-in on `https://boxferry.dev`.
Local previews and other origins never load it. The footer's **Privacy settings** link reopens
the native form. Analytics is unchecked initially; **Accept** saves selected categories and
**Reject** rejects Analytics. Preferences expire after 180 days.

## Current account status

The measurement ID is `G-TX06VP39B2`. The maintainer confirmed event-data retention of **2 months**
and user-data retention of **14 months**. These differ from cookie lifetime and aggregated reports.

Collection is enabled by `project.extra.analytics.enabled = true` in `zensical.toml`.
On 5 November 2026, the maintainer confirmed:

1. **Enhanced Measurement / Optimierte Analysen** is off for the BoxFerry web stream.
2. Google Signals and advertising personalization were switched off.
3. Optional **Google products & services** account data sharing was already unchecked/off;
   its setting was not changed. This control applies to every property in that Analytics account.

The maintainer also confirmed that property-level user-provided data collection is off.
These are maintainer-reported account settings; the website build does not inspect or change the
Google account. Review them again after account changes, including connected advertising products.
Collection can be stopped with the same flag without removing the banner.

Google has a separate tag-level configuration under the web stream's **Google tag** settings.
Use **Show all** to review automatic event detection and user-provided data capabilities. The
maintainer explicitly keeps these tag-level capabilities enabled. Destination-level settings and
tag capabilities have different scopes; a capability being present does not prove data
transmission. Property-level user-provided data collection remains off and advertising-data
consent remains denied. Validate actual page-view counts and transmitted fields before activation;
do not mix manual and automatic views without checking for duplicates.
See [Google's tag configuration guide](https://support.google.com/analytics/answer/12131703?hl=en).

Detailed location/device collection also remains enabled at the maintainer's explicit choice.
The privacy notice covers city, screen resolution and detailed browser/device information.
These optional account settings do not authorize collection before a visitor's Analytics opt-in.

[Google documents](https://support.google.com/analytics/answer/3379636?hl=en) that its data-processing
terms are already incorporated for direct Analytics customers established in the EEA, UK or
Switzerland. This provider statement does not verify this account's legal entity, contacts or
agreements. The maintainer remains responsible for those details and the separate Hetzner checks
in [legal-maintenance.md](legal-maintenance.md).

The Google tag owns the initial view with `send_page_view: true`; the adapter sends no manual
initial event. Later completed instant-navigation views are sent manually, with canonical-path
deduplication. Destination Enhanced Measurement stays off to prevent independent history views.
Tag-level detection capabilities remain enabled at the maintainer's choice.

The clarified notice uses policy version `2026-11-05-ga4-v2`; a previous v1 choice cannot authorize
collection until the visitor makes a fresh choice. Do not paste a `gtm.js` snippet into the site:
this integration uses GA4's `/gtag/js` endpoint. See [ADR 0008](decisions/0008-initial-and-navigation-analytics.md).

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
