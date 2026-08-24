#!/usr/bin/env bash

set -Eeuo pipefail

usage() {
  cat << 'EOF'
Usage: prepare-hetzner-server.sh

Prepare the Hetzner release directories and atomically install the fixed version updater.

Required environment variables:
  BOXFERRY_DEPLOY_HOST
  BOXFERRY_DEPLOY_PORT
  BOXFERRY_DEPLOY_USER
  BOXFERRY_DEPLOY_ROOT

Optional environment variable:
  BOXFERRY_ADMIN_SSH_IDENTITY_FILE

The SSH identity must be an unrestricted administrator identity. The restricted rsync and
version-updater identities cannot prepare the server.
EOF
}

fail() {
  printf 'BoxFerry Hetzner preparation failed: %s\n' "$1" >&2
  exit 2
}

if (($# != 0)); then
  if (($# == 1)) && [[ "$1" == --help ]]; then
    usage
    exit 0
  fi
  usage >&2
  exit 2
fi

required_variables=(
  BOXFERRY_DEPLOY_HOST
  BOXFERRY_DEPLOY_PORT
  BOXFERRY_DEPLOY_USER
  BOXFERRY_DEPLOY_ROOT
)
for variable in "${required_variables[@]}"; do
  [[ -n "${!variable:-}" ]] || fail "required value is empty: ${variable}"
done

[[ "${BOXFERRY_DEPLOY_HOST}" =~ ^[A-Za-z0-9][A-Za-z0-9.-]*$ ]] ||
  fail "BOXFERRY_DEPLOY_HOST contains unsafe characters"
[[ "${BOXFERRY_DEPLOY_USER}" =~ ^[A-Za-z0-9_][A-Za-z0-9._-]*$ ]] ||
  fail "BOXFERRY_DEPLOY_USER contains unsafe characters"
[[ "${BOXFERRY_DEPLOY_PORT}" =~ ^[0-9]+$ ]] ||
  fail "BOXFERRY_DEPLOY_PORT must be a decimal port number"
deploy_port=$((10#${BOXFERRY_DEPLOY_PORT}))
((deploy_port >= 1 && deploy_port <= 65535)) ||
  fail "BOXFERRY_DEPLOY_PORT must be between 1 and 65535"

deploy_root=${BOXFERRY_DEPLOY_ROOT}
if [[ ! "${deploy_root}" =~ ^/[A-Za-z0-9._/-]+$ ||
  "${deploy_root}" == / || "${deploy_root}" == */ ||
  "${deploy_root}" == *//* || "${deploy_root}" == *'/./'* ||
  "${deploy_root}" == */. || "${deploy_root}" == *'/../'* ||
  "${deploy_root}" == */.. ]]; then
  fail "BOXFERRY_DEPLOY_ROOT must be a safe absolute directory"
fi

script_directory="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repository_root="$(cd -- "${script_directory}/.." && pwd -P)"
updater_source="${repository_root}/deployment/hetzner/version-updater.sh"
[[ -f "${updater_source}" && ! -L "${updater_source}" ]] ||
  fail "tracked version updater is missing or unsafe"

ssh_options=(-p "${BOXFERRY_DEPLOY_PORT}")
scp_options=(-P "${BOXFERRY_DEPLOY_PORT}")
administrator_identity=${BOXFERRY_ADMIN_SSH_IDENTITY_FILE:-}
if [[ -n "${administrator_identity}" ]]; then
  [[ -f "${administrator_identity}" && -r "${administrator_identity}" ]] ||
    fail "BOXFERRY_ADMIN_SSH_IDENTITY_FILE is not a readable file"
  ssh_options+=(-i "${administrator_identity}" -o IdentitiesOnly=yes)
  scp_options+=(-i "${administrator_identity}" -o IdentitiesOnly=yes)
fi

remote="${BOXFERRY_DEPLOY_USER}@${BOXFERRY_DEPLOY_HOST}"
remote_updater="${deploy_root}/.deploy/version-updater.sh"
remote_upload="${remote_updater}.upload"
prepare_command="install -d -m 700 -- '${deploy_root}/.deploy' && "
prepare_command+="install -d -m 755 -- '${deploy_root}/incoming' '${deploy_root}/releases'"
activate_command="chmod 700 -- '${remote_upload}' && "
activate_command+="mv -f -- '${remote_upload}' '${remote_updater}' && "
activate_command+="test -x '${remote_updater}' && test ! -L '${remote_updater}'"

printf 'Preparing %s on %s:%s with the unrestricted administrator identity.\n' \
  "${deploy_root}" "${BOXFERRY_DEPLOY_HOST}" "${BOXFERRY_DEPLOY_PORT}"
# Connection values and paths are validated above; client-side expansion is deliberate.
# shellcheck disable=SC2029
ssh "${ssh_options[@]}" "${remote}" "${prepare_command}"
scp "${scp_options[@]}" "${updater_source}" "${remote}:${remote_upload}"
# Connection values and paths are validated above; client-side expansion is deliberate.
# shellcheck disable=SC2029
ssh "${ssh_options[@]}" "${remote}" "${activate_command}"

printf 'Hetzner server preparation completed.\n'
printf 'Next: run the Production deployment workflow with show-authorized-keys.\n'
