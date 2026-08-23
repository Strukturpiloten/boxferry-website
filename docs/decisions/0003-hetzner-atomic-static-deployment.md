# 0003: Hetzner atomic static deployment

- Status: Accepted
- Date: 2026-08-23

## Context

The assembled site is static but contains many HTML, JavaScript, search, image, metadata, and
Rustdoc files. Synchronizing directly into the served directory would expose mixed releases. A
normal SSH key for the shared hosting account could also access unrelated websites owned by that
Unix user. Git is available on the server, but generated site output is deliberately untracked and
must be built from exact source revisions in CI.

## Decision

Build and validate the complete locked-source artifact in GitHub Actions. Transfer it with a
dedicated key forced to write-side `rrsync` below an unserved `incoming/` directory. Use a second key
forced through `flock` to a repository-owned version updater. The updater validates an exact website
revision, moves the staging directory into immutable `releases/<sha>/` storage, rotates four
previous links from oldest to newest, and replaces `current` last.

Serve `/usr/www/users/c3diiy/dev_boxferry/current` through Apache. Retain `current` plus
`previous-1` through `previous-4`. Verify the public HTTPS revision and server policy after activation
but before finalization; restore the complete saved link state on failure. Permit a retained release
to be promoted through the same verified transaction.

Copy a tracked `.htaccess` policy into every generated release. It owns directory-index behavior,
static content types, security headers, cache revalidation, release-manifest denial, and the
same-origin browser policy. Do not run PHP or a documentation build on the webserver. Do not use Git
as an artifact transport and do not commit generated site output.

Store private keys only as protected GitHub environment secrets. Derive and print the public keys
and complete restricted `authorized_keys` entries on every authorized run. Pin the SSH host key and
restrict deployment operations to `main` and the `production` environment.

## Consequences

- Public requests see either the complete old release or the complete new release.
- Four named previous links provide observable history and verified rollback without rebuilding.
- The upload key cannot modify active releases, links, or the updater through the allowed rsync path.
- The updater key cannot request an interactive shell or choose another executable.
- Both keys still authenticate as the shared Unix account; forced commands reduce capability but do
  not provide the hard filesystem isolation of a separate hosting account or chroot.
- The updater requires one-time manual installation and manual replacement when its tracked source
  changes.
- Apache override compatibility, DNS, and TLS must be established before the first deployment can
  pass external verification.
