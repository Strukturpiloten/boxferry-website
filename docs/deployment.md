# Production deployment

BoxFerry is deployed as a static Zensical artifact. Apache serves HTML, JavaScript, CSS, images,
JSON, Rustdoc, and plain-text files directly. The webserver does not run PHP or build documentation.

## Server layout

The Hetzner domain document root is:

```text
/usr/www/users/c3diiy/dev_boxferry/current
```

The deployment root has this contract:

```text
dev_boxferry/
├── .deploy/
│   ├── version-updater.sh
│   └── version-updater.lock
├── incoming/
├── releases/
│   └── <website-commit-sha>/
├── current -> releases/<newest-sha>
├── previous-1 -> releases/<one-release-back>
├── previous-2 -> releases/<two-releases-back>
├── previous-3 -> releases/<three-releases-back>
└── previous-4 -> releases/<oldest-retained-sha>
```

Only `current` is served. The four `previous-*` links expose an ordered, human-readable rollback
history. A successful sixth deployment removes the release that is no longer referenced.

## Apache policy

The tracked source is `deployment/apache/.htaccess`. `scripts/prepare_deployment.py` copies it to
`site/.htaccess`; rsync then uploads it with every immutable release. Do not install a separate
copy manually.

The policy declares `index.html`, disables directory listings, assigns static MIME types and UTF-8,
denies access to the private release manifest, adds browser security headers, and prevents stale
HTML and metadata. It also applies a same-origin content policy compatible with Zensical and
Rustdoc. Zensical uses local system fonts, so the production artifact makes no Google Fonts request.

Hetzner must permit the equivalent of `AllowOverride AuthConfig FileInfo Indexes Options=Indexes`
and provide `mod_authz_core`, `mod_headers`, `mod_mime`, and `mod_dir`. Deployment verifies the
security headers, the denied release manifest, and disabled directory listing before finalization.
An incompatible Apache policy therefore causes automatic rollback.

## One-time Hetzner bootstrap

Create the private deployment directories with the normal administrator SSH access:

```console
ssh c3diiy@www734.your-server.de -p 222 \
  'install -d -m 700 /usr/www/users/c3diiy/dev_boxferry/.deploy && install -d -m 755 /usr/www/users/c3diiy/dev_boxferry/incoming /usr/www/users/c3diiy/dev_boxferry/releases'
```

Copy the fixed-command updater from this repository, then make it owner-executable:

```console
scp -P 222 deployment/hetzner/version-updater.sh \
  c3diiy@www734.your-server.de:/usr/www/users/c3diiy/dev_boxferry/.deploy/version-updater.sh
ssh c3diiy@www734.your-server.de -p 222 \
  'chmod 700 /usr/www/users/c3diiy/dev_boxferry/.deploy/version-updater.sh'
```

The updater derives its deployment root from its `.deploy/` location. It accepts exactly one
request line on standard input, rejects requested SSH commands and unsafe paths, validates the
release manifest and public metadata, rejects symlinks inside releases, and updates `current` last.

Install an updated copy manually whenever the tracked updater changes. The rsync-only key cannot
overwrite `.deploy/`, and the updater-only key cannot execute a file-transfer command.

## GitHub production environment

Create an environment named `production`. Restrict it to `main` and configure the desired required
reviewer. The workflow also rejects production operations selected from another branch.

Create these environment variables:

| Variable                      | Value                                                    |
| ----------------------------- | -------------------------------------------------------- |
| `BOXFERRY_DEPLOY_HOST`        | `www734.your-server.de`                                  |
| `BOXFERRY_DEPLOY_PORT`        | `222`                                                    |
| `BOXFERRY_DEPLOY_USER`        | `c3diiy`                                                 |
| `BOXFERRY_DEPLOY_ROOT`        | `/usr/www/users/c3diiy/dev_boxferry`                     |
| `BOXFERRY_SITE_ORIGIN`        | `https://boxferry.dev`                                   |
| `BOXFERRY_DEPLOY_KNOWN_HOSTS` | Verified complete known-hosts line for host and port 222 |

Obtain the host key, then verify its fingerprint against the already trusted administrator SSH
connection or Hetzner support before storing it. `ssh-keyscan` alone does not authenticate a host.

```console
ssh-keyscan -p 222 -t ed25519 www734.your-server.de
```

Create these environment secrets:

- `BOXFERRY_RSYNC_SSH_PRIVATE_KEY`
- `BOXFERRY_VERSION_UPDATER_SSH_PRIVATE_KEY`

Both must be dedicated Ed25519 private keys. Private keys are secrets, never variables. Their public
keys are deliberately not stored: every production-authorized workflow run derives them with
`ssh-keygen -y`, verifies their shape, and prints complete `authorized_keys` entries and fingerprints
in the log and job summary.

Generate the two keys outside the repository:

```console
ssh-keygen -t ed25519 -a 100 -N '' -f boxferry-website-rsync \
  -C boxferry-website-rsync
ssh-keygen -t ed25519 -a 100 -N '' -f boxferry-website-version-updater \
  -C boxferry-website-version-updater
```

Add only the private file contents to GitHub environment secrets. Do not commit either key.

## Install or rotate deployment keys

Run the `Production deployment` workflow on `main` with `show-authorized-keys`. Copy the two printed
lines into `~/.ssh/authorized_keys` on Hetzner. The upload entry forces write-side `/usr/bin/rrsync`
below `incoming/`; the updater entry forces `/usr/bin/flock` around `version-updater.sh`.

For rotation:

1. Replace one or both private-key environment secrets.
2. Run `show-authorized-keys`.
3. Add the new printed lines without removing the old lines.
4. Run a production deployment or an SSH protocol test.
5. Remove the old lines only after the new keys succeed.

## Deploy

Run the `Production deployment` workflow on `main` with `deploy`. It:

1. builds and validates exact locked documentation revisions without production secrets;
2. uploads the complete hidden-file-inclusive `site/` artifact;
3. prints the restricted key entries again;
4. pins the configured SSH host identity;
5. uses the rsync key to upload to `incoming/<sha>-<run-id>-<attempt>/`;
6. uses the updater key to activate the immutable SHA directory and rotate history links;
7. verifies HTTPS, revision metadata, homepage, documentation, Apache headers, private-manifest
   denial, and disabled directory listing;
8. finalizes retention only after verification.

Failure between activation and verification sends `rollback <sha>` through the updater key and
restores the complete prior link state. Finalization deletes only a validated, unreferenced sixth
release.

## Roll back a finalized deployment

Inspect retained revisions through the administrator connection:

```console
ssh c3diiy@www734.your-server.de -p 222 \
  'cd /usr/www/users/c3diiy/dev_boxferry && ls -l current previous-1 previous-2 previous-3 previous-4'
```

Run `Production deployment` with `rollback` and enter the exact retained 40-character SHA. The
updater promotes that retained directory, moves the prior current release to `previous-1`, preserves
all five releases, verifies the public revision and security headers, and finalizes. Failed rollback
verification restores the complete original link state.

## DNS and TLS

Point `boxferry.dev` at the Hetzner webspace, configure the document root to the `current` path, and
enable a valid certificate before the first production deployment. The generated Apache policy sets
one-year HSTS for the domain without `includeSubDomains` or preload. The workflow refuses non-HTTPS
origins and does not finalize a release that fails HTTPS verification.
