# 0005: Shared validation and dependency admission

- Status: Accepted; publication triggering partially superseded by [0006](0006-validated-main-publication.md)
- Date: 2026-11-03

## Decision

Consume BoxFerry's immutable development automation through a narrow manifest, shared setup,
planner, gate and common Renovate preset. Keep website-specific assembly, strict rendering,
privacy, route, source-lock and deployment checks here. This creates no Rust product dependency
and adds no Rust product test suite.

Pull requests and merge queues select checks using policy from their exact trusted base.
Maintenance prose and public site prose have separate tasks. Unknown, mixed configuration and
source changes use the complete pipeline. Main, manual and local complete validation remain
complete, including first-party Rust API artifacts and deployment-artifact verification.

Adopt in two stages: complete-only manifest, service and policy first, then selective callers.
Dependency admission always uses the automation revision recorded on the trusted base, including
when a candidate proposes another automation revision. The default-branch service evaluates
metadata without candidate-code execution; candidate readers have read permissions only.

Ordinary third-party updates retain 72 hours. Published isolated first-party updates include their
necessary transitive resolution without an age hold. Automatic dependency merging remains subject
to compatibility and integrity checks and does not publish the site. Protected production
deployment remains a separately requested operator action under ADR 0003.

Before the first automation release tag, the shared infrastructure exception in BoxFerry ADR 0092
permits a reviewed full commit SHA with an honest bootstrap comment. It grants no release or
deployment authority. Rollback restores the previous reviewed manifest, workflows and preset SHA.

The publication separation above is superseded by [0006](0006-validated-main-publication.md). Dependency admission and exact-candidate validation remain unchanged.
