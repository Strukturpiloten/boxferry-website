#!/usr/bin/env bash

set -Eeuo pipefail

script_directory="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repository_root="$(cd -- "${script_directory}/.." && pwd -P)"
cd -- "${repository_root}"

base_ref="${1:-origin/main}"
base_sha="$(git rev-parse --verify "${base_ref}^{commit}" 2> /dev/null || true)"
if [[ ! "${base_sha}" =~ ^[0-9a-f]{40}$ ]]; then
  printf 'No valid comparison revision for %s; running the complete gate.\n' "${base_ref}" >&2
  exec ./scripts/check-all.sh --check
fi

profile="$(python3 scripts/validation-plan.py --base "${base_sha}")"
printf 'Website local validation profile: %s\n' "${profile}"
if [[ "${profile}" == maintenance ]]; then
  exec ./scripts/check-maintenance-docs.sh
fi
exec ./scripts/check-all.sh --check
