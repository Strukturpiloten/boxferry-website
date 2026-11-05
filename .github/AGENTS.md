# GitHub automation guidance

The [root guidance](../AGENTS.md) applies. Follow the [shared automation guide](https://github.com/Strukturpiloten/boxferry/blob/main/docs/automation.md) and [website development guide](../docs/development.md) for trusted-base bindings, change-aware feedback, and the complete gate. Keep the manifest, workflows, and preset on one reviewed immutable revision. Preserve exact documentation-source locks and the [deployment runbook](../docs/deployment.md)'s historical toolchain exception, artifact retention, and rollback. Routine website publication follows the maintainer-authorized successful-main-CI policy in
[ADR 0006](../docs/decisions/0006-validated-main-publication.md). Preserve its exact-revision and
stale-candidate guards and any configured environment approval. Manual bootstrap, rollback and
key operations still require an explicit operator request. This policy grants no publication
authority for another repository.
