# 0006: Publish validated current main automatically

- Status: Accepted
- Date: 2026-11-05
- Partially supersedes: [0003](0003-hetzner-atomic-static-deployment.md) and
  [0005](0005-shared-validation-and-dependency-admission.md), publication triggering only

## Context

Manual-only publication was introduced while shared CI was being adopted. Main now runs the
complete locked-source gate. The maintainer explicitly requested automatic Hetzner publication
after successful main validation, including the approved company referral links and wider layout.
The existing atomic publisher, environment, restricted keys and retained releases remain useful.

## Decision

CI validation jobs remain read-only and have no production secrets. A main push calls the reusable
`Production deployment` workflow only after `Required CI` succeeds. The caller passes its exact
SHA and deploy-only automatic intent. The request selector independently validates the caller's
push payload, repository, branch and matching explicit SHA. Pull requests, forks, merge groups,
manual CI and failed validation cannot authorize automatic publication.

Use `workflow_call`, not a privileged `workflow_run` completion trigger. The publication call
forwards only the named restricted upload and updater keys for existing repository-level setups.
Protected environment secrets take precedence in production jobs. There is no blanket secret
inheritance, and validation steps receive neither SSH key in their environment. Main push CI has a separate concurrency lane from manual CI; read-only manual runs cannot replace
its pending publication. Main CI and production never cancel an active publication. PR and
merge-group validation retain cancellation because they cannot publish.

Automatic requests select only `deploy`. The tested SHA must equal current main during request
admission and again in the publisher before artifact download or SSH-key preparation. A superseded
automatic request is a documented skip, not a fallback to a different revision. Existing production
concurrency remains serialized without canceling an active update. This prevents a delayed old CI
validation result from restoring an obsolete main revision over a newer release.

Rebuild and validate the exact selected revision with locked documentation sources before entering
the protected production environment. Download only that build's SHA-named artifact from the same
deployment run. Preserve environment protections, pinned SSH host identity, restricted upload and
updater keys, atomic activation, public revision/security checks, error rollback and retention.

Keep explicit manual key rendering, first bootstrap, deploy and retained-artifact rollback. Manual
deploy may intentionally select an older revision from main history; its historical toolchain
verification remains unchanged. A subsequent successful main push publishes current main again.
Automatic publication never attempts bootstrap or changes the server updater installation.

## Ownership and dependencies

The canonical definitions are this repository's `ci.yml`, `deploy.yml` and request selector. The
website is the sole publisher of `boxferry.dev`; BoxFerry and Lens release workflows remain separate
and do not gain publication authority. Their native suites and runtime selection are unchanged.
Website main CI intentionally avoids cancellation because it includes publication; other products'
read-only validation workflows do not share that requirement.

No software, action, toolchain or documentation-source pin changes. The existing GitHub Actions
manager owns the unchanged workflow paths; shared Renovate grouping, approvals, age holds and
integrity records remain unchanged. The first-party reusable workflow uses GitHub's standard `./`
reference, which resolves to the caller's exact commit and needs no separately moving version pin.
Pinned actionlint does not support the newer `$/` spelling. A single explained `self-repository`
style annotation retains compatibility; all trigger, permission and integrity audits remain enabled.
The selector uses Python's standard library and is covered by
the existing script linting, type checking and unit-test discovery.

## Consequences

- Merging a website or documentation-source update can publish it after complete main validation.
- Operators inspect main CI's publication jobs; configured environment approval
  still applies. This repository currently has no required production reviewer.
- A newer main commit can supersede an otherwise successful automatic candidate. The next current
  candidate must pass its own CI; no partial result authorizes deployment.
- This authorization covers the website only. It adds no Analytics and grants no authority to
  release or deploy another workspace product.
