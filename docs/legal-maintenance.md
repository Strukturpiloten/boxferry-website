# Legal-page maintenance

The English legal notice and privacy policy are website-owned content. Keep their existing
`/legal-notice/` and `/privacy-policy/` routes and shared footer links. No German translations or
visitor acceptance step are required by this repository's current presentation contract.

## Provider and contact changes

Keep the provider and GDPR controller as Strukturpiloten OHG. The content contact is Martin
Beckert; this designation is separate from the company's legal representatives or an appointed
data protection officer. Keep email, visible telephone number, `mailto:` and `tel:` targets
consistent in both pages. Do not assert that Section 18(2) MStV applies without assessing the
actual content offering.

## Hosting facts to verify before publication

The following account-specific checks are still pending. Provider documentation, source tests
and a passing build do not establish the current hosting configuration or legal compliance.

- Confirm the company's address, legal representatives, register and VAT details.
- Confirm the hosting product and server location match the privacy policy.
- Confirm the applicable data processing agreement with Hetzner is in place.
- In konsoleH, inspect **Settings > Account maintenance** and record the actual Apache access/error
  log deletion period. Check any separately retained or exported logs and incident copies.
- Confirm the applicable backup retention and whether deleted logs remain in backups.
- Replace the provider-default explanation with the verified account-specific retention period
  before publishing this legal revision. Do not invent a period or claim settings were changed.

[Hetzner's data-protection documentation](https://docs.hetzner.com/general/company-and-policy/data-protection-at-hetzner/)
was checked on 6 October 2026. It states a configurable seven-day default for Apache access/error
logs and separately describes encrypted backups retained for 14 days. The default is not proof
of this account's setting. The same documentation explains how to conclude a data processing
agreement; do not disclose customer-account credentials or contract contents in the repository.

## Browser and site checks

- Verify theme storage against the pinned Zensical version and active features, not a stale build.
- Describe only the selected color scheme while linked content-tab persistence is disabled.
- Check cookies and browser network/storage behavior on the actual deployed site; no analytics,
  tracking, remote fonts or third-party scripts are authorized by these text changes.
- Preserve local search, existing English legal routes and footer access to both pages.
- Run the repository gate before a later commit or PR. Content tests prevent regressions; they
  do not prove host operations or determine whether consent is legally required.

Legal-content edits add no dependency or Renovate extraction path. Review any accompanying
toolchain changes separately under the dependency policy. These edits do not configure log
deletion, conclude a contract, publish or deploy the website.
