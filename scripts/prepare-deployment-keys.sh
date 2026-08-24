#!/usr/bin/env bash
set -Eeuo pipefail

required_variables=(
  BOXFERRY_DEPLOY_ROOT
  BOXFERRY_RSYNC_SSH_PRIVATE_KEY
  BOXFERRY_VERSION_UPDATER_SSH_PRIVATE_KEY
  GITHUB_STEP_SUMMARY
  RUNNER_TEMP
)
for variable in "${required_variables[@]}"; do
  [[ -n "${!variable:-}" ]] || {
    printf 'Required deployment value is empty: %s\n' "${variable}" >&2
    exit 2
  }
done

keys_directory="${RUNNER_TEMP}/boxferry-deployment-keys"
readonly keys_directory
install -d -m 700 -- "${keys_directory}"
install -m 600 /dev/null "${keys_directory}/rsync"
install -m 600 /dev/null "${keys_directory}/version-updater"
printf '%s\n' "${BOXFERRY_RSYNC_SSH_PRIVATE_KEY}" > "${keys_directory}/rsync"
printf '%s\n' "${BOXFERRY_VERSION_UPDATER_SSH_PRIVATE_KEY}" > \
  "${keys_directory}/version-updater"

ssh-keygen -y -f "${keys_directory}/rsync" > "${keys_directory}/rsync.pub"
ssh-keygen -y -f "${keys_directory}/version-updater" > \
  "${keys_directory}/version-updater.pub"
python3 scripts/render_authorized_keys.py \
  --deployment-root "${BOXFERRY_DEPLOY_ROOT}" \
  --rsync-public-key "${keys_directory}/rsync.pub" \
  --updater-public-key "${keys_directory}/version-updater.pub" \
  > "${keys_directory}/authorized_keys"

printf 'Copy these two lines into ~/.ssh/authorized_keys:\n\n'
cat "${keys_directory}/authorized_keys"
printf '\nPublic-key fingerprints:\n'
ssh-keygen -lf "${keys_directory}/rsync.pub"
ssh-keygen -lf "${keys_directory}/version-updater.pub"

{
  printf '## Restricted deployment keys\n\n'
  printf "Copy these two lines into \`~/.ssh/authorized_keys\`:\n\n"
  printf '```text\n'
  cat "${keys_directory}/authorized_keys"
  printf '```\n\n'
  printf 'Public-key fingerprints:\n\n'
  printf '```text\n'
  ssh-keygen -lf "${keys_directory}/rsync.pub"
  ssh-keygen -lf "${keys_directory}/version-updater.pub"
  printf '```\n'
} >> "${GITHUB_STEP_SUMMARY}"
