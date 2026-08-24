# Production deployment

BoxFerry publishes a static Zensical site to Hetzner. GitHub Actions builds every release; the
server only stores and serves generated HTML, JavaScript, CSS, images, JSON, text, and Rustdoc.

Use the protected `Production deployment` workflow for every publication. Nothing deploys on a
push, merge, or pull request.

## Choose the right operation

| Operation                   | Runs where     | Use it for                                     |
| --------------------------- | -------------- | ---------------------------------------------- |
| `prepare-hetzner-server.sh` | Local checkout | Create directories and install the updater     |
| `show-authorized-keys`      | GitHub Actions | Print the two restricted server key entries    |
| `bootstrap`                 | GitHub Actions | Create the first release and `current` link    |
| `deploy`                    | GitHub Actions | Publish and publicly verify a release          |
| `rollback`                  | GitHub Actions | Promote and verify a retained previous release |

The local preparation script and the workflow `bootstrap` operation are different steps. Server
preparation uses an unrestricted administrator identity. Workflow operations use restricted keys.

## Before the first publication

You need:

- administrator access to the BoxFerry website repository;
- an unrestricted SSH login for the Hetzner account;
- a clean local checkout of `boxferry-website` on `main`;
- local `ssh`, `scp`, `ssh-keygen`, and `ssh-keyscan` commands;
- `/usr/bin/rrsync` and `/usr/bin/flock` on Hetzner.

The Hetzner account must allow an Apache document root below
`/absolute/path/to/dev_boxferry`. Apache must honor the tracked `.htaccess` rules.

## 1. Create the GitHub environment

In the repository, open **Settings → Environments → New environment** and create `production`.

Configure the environment to:

1. allow deployments only from `main`;
2. require the desired reviewer;
3. prevent administrators from bypassing the protection if that matches the project policy.

Create these environment variables, not repository-level variables:

| Variable                      | Value                                     |
| ----------------------------- | ----------------------------------------- |
| `BOXFERRY_DEPLOY_HOST`        | `<host>`                                  |
| `BOXFERRY_DEPLOY_PORT`        | `<port>`                                  |
| `BOXFERRY_DEPLOY_USER`        | `<username>`                              |
| `BOXFERRY_DEPLOY_ROOT`        | `/absolute/path/to/dev_boxferry`          |
| `BOXFERRY_SITE_ORIGIN`        | `https://boxferry.dev`                    |
| `BOXFERRY_DEPLOY_KNOWN_HOSTS` | `ssh-keyscan -p <port> -t ed25519 <host>` |

### Verify the SSH host record

Collect the server's Ed25519 host record:

```console
ssh-keyscan -p <port> -t ed25519 <host>
```

The value stored in `BOXFERRY_DEPLOY_KNOWN_HOSTS` is the complete output line. It has this shape:

```text
[<host>]:<port> ssh-ed25519 AAAA...
```

Before storing it, compare its fingerprint with the key seen through the existing trusted
administrator connection or with a fingerprint supplied by Hetzner. `ssh-keyscan` discovers a key;
it does not prove that the key belongs to the intended server.

## 2. Create the restricted deployment keys

Generate two independent Ed25519 keys without passphrases outside the repository. GitHub Actions
cannot answer a key passphrase prompt.

```console
boxferry_key_directory="${XDG_CONFIG_HOME:-${HOME}/.config}/boxferry/deployment"
install -d -m 700 "${boxferry_key_directory}"

ssh-keygen -t ed25519 -a 100 -N '' \
  -f "${boxferry_key_directory}/rsync" \
  -C boxferry-website-rsync
ssh-keygen -t ed25519 -a 100 -N '' \
  -f "${boxferry_key_directory}/version-updater" \
  -C boxferry-website-version-updater
```

Create these `production` environment secrets:

| Secret                                     | File to copy                                |
| ------------------------------------------ | ------------------------------------------- |
| `BOXFERRY_RSYNC_SSH_PRIVATE_KEY`           | `${boxferry_key_directory}/rsync`           |
| `BOXFERRY_VERSION_UPDATER_SSH_PRIVATE_KEY` | `${boxferry_key_directory}/version-updater` |

Copy the complete private file, including its `BEGIN` and `END` lines. Do not use the `.pub` file,
put a private key in a variable, commit either key, or paste a key into an issue or workflow log.

Keep the local `.pub` files until the installation fingerprints have been compared. Store or remove
the local private files according to the project's credential-backup policy after deployment works.

## 3. Prepare the Hetzner server

Update the local checkout, then export the same four connection values used in GitHub:

```console
git switch main
git pull --ff-only

export BOXFERRY_DEPLOY_HOST=<host>
export BOXFERRY_DEPLOY_PORT=<port>
export BOXFERRY_DEPLOY_USER=<username>
export BOXFERRY_DEPLOY_ROOT=/absolute/path/to/dev_boxferry
```

If the administrator key is not selected by the SSH agent or normal SSH configuration, provide its
local path:

```console
export BOXFERRY_ADMIN_SSH_IDENTITY_FILE=/absolute/path/to/administrator-key
```

Run the preparation helper from the repository root:

```console
./scripts/prepare-hetzner-server.sh
```

The helper:

1. rejects unsafe or missing connection values;
2. creates `.deploy/`, `incoming/`, and `releases/` with their required permissions;
3. uploads `deployment/hetzner/version-updater.sh` to a temporary path;
4. atomically replaces the installed updater and verifies that it is executable.

It is safe to rerun when the tracked updater changes. It does not create a release, edit
`authorized_keys`, or use either restricted deployment key.

## 4. Authorize the restricted keys

Run **Production deployment** on `main` with `show-authorized-keys`. Approve the `production`
environment when requested.

The workflow derives public keys from the two secrets and prints:

- one entry forced to write-side `/usr/bin/rrsync` below `incoming/`;
- one entry forced through `/usr/bin/flock` to the installed updater.

Compare the two workflow fingerprints with the local public keys:

```console
ssh-keygen -lf "${boxferry_key_directory}/rsync.pub"
ssh-keygen -lf "${boxferry_key_directory}/version-updater.pub"
```

Using the unrestricted administrator connection, paste the two complete workflow lines into
`~/.ssh/authorized_keys`. Keep each entry on exactly one line. Existing unrelated entries remain in
the file.

The workflow prints these entries again during every deployment. Their comments are labels only;
the forced commands enforce the restriction.

## 5. Bootstrap the first release

Hetzner cannot select `current` as the document root before that link exists. Run **Production
deployment** on `main` with `bootstrap` once.

Bootstrap still builds and validates the complete immutable site. It then uploads the artifact and
asks the server updater to create and finalize the first release. It skips only public-origin checks
because `boxferry.dev` cannot serve `current` yet.

The server permits bootstrap only when release storage and all history links are empty. Repeating
the same initial revision is safe. A later release cannot use bootstrap to bypass verification.

After success, confirm that the link exists through the administrator connection:

```console
ssh <username>@<host> -p <port> \
  'cd /absolute/path/to/dev_boxferry && ls -l current releases'
```

If bootstrap reports non-empty release history, do not delete directories blindly. Inspect
`.deploy/pending-release`, `current`, `previous-*`, and `releases/` before recovery.

## 6. Connect the domain

In the Hetzner web interface:

1. set the `boxferry.dev` document root to
   `<absolute/path/to/dev_boxferry>/current`;
2. point the domain's DNS records at the webspace;
3. enable a valid TLS certificate for `boxferry.dev`.

Check that Apache now serves the bootstrapped release:

```console
curl --fail --silent --show-error --head https://boxferry.dev/
curl --fail --silent --show-error https://boxferry.dev/assets/data/deployment.json
```

A 404 at this point normally means that the document root still points somewhere other than
`current`.

## 7. Verify with a normal deployment

Run **Production deployment** on `main` with `deploy`. Running it for the same revision as bootstrap
is supported and performs the public checks that bootstrap intentionally skipped.

A successful normal deployment verifies:

- HTTPS revision metadata, the homepage, and documentation routes;
- the content security policy, HSTS, and MIME protection headers;
- denial of the private release manifest;
- disabled directory listings.

The first publication is complete only after this normal deployment succeeds.

## Routine deployment

For later releases:

1. merge the website changes into `main`;
2. rerun `prepare-hetzner-server.sh` first if the tracked updater changed;
3. run **Production deployment** on `main` with `deploy`;
4. approve the protected environment and check the job summary.

The workflow builds exact locked documentation revisions without production secrets, uploads the
complete artifact to `incoming/`, activates the SHA-named release, verifies the public server, and
then finalizes retention. A verification failure restores the complete previous link state.

## Roll back

Inspect the retained revisions with the unrestricted administrator connection:

```console
ssh <username>@<host> -p <port> \
  'cd /absolute/path/to/dev_boxferry && ls -l current previous-1 previous-2 previous-3 previous-4'
```

Run **Production deployment** with `rollback` and enter the exact retained 40-character SHA. The
workflow promotes that release, verifies it through `https://boxferry.dev`, and restores the prior
links if verification fails.

## Rotate deployment keys

Rotate one or both restricted keys without an outage:

1. generate a replacement Ed25519 key outside the repository;
2. replace its `production` environment secret;
3. run `show-authorized-keys`;
4. compare the fingerprint and add the new line without removing the old line;
5. run a normal deployment;
6. remove the old `authorized_keys` line only after the new key succeeds.

The local server-preparation script uses the administrator identity and is unaffected by restricted
key rotation.

## Server layout and retention

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

Apache serves only `current`. A successful sixth deployment deletes the release no longer
referenced by these five links.

Every release contains the tracked `deployment/apache/.htaccess`. Hetzner must permit the equivalent
of `AllowOverride AuthConfig FileInfo Indexes Options=Indexes` and provide `mod_authz_core`,
`mod_headers`, `mod_mime`, and `mod_dir`. The server runs neither PHP nor a documentation build.

## Troubleshooting

| Symptom                                          | Check first                                                   |
| ------------------------------------------------ | ------------------------------------------------------------- |
| Administrator preparation gets permission denied | Use the unrestricted administrator identity, not a forced key |
| Restricted key authentication fails              | Rerun `show-authorized-keys` and compare fingerprints         |
| `bootstrap` rejects non-empty history            | Inspect pending state, links, and releases before recovery    |
| `current` exists but the domain returns 404      | Correct the Hetzner document root                             |
| HTTPS verification fails                         | Check DNS, TLS, Apache overrides, and `.htaccess` support     |
| A normal deployment rolls back                   | Read the failed public check before retrying                  |
