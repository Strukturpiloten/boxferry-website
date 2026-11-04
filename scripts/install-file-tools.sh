#!/usr/bin/env bash

set -Eeuo pipefail

if (($# > 2)); then
  printf 'Usage: %s [install-directory] [--lychee-only]\n' "$0" >&2
  exit 2
fi
install_directory="${1:-/usr/local/bin}"
install_mode="${2:-full}"
case "${install_mode}" in
  full) selection=(--profile website) ;;
  --lychee-only) selection=(--tools lychee) ;;
  *)
    printf 'Usage: %s [install-directory] [--lychee-only]\n' "$0" >&2
    exit 2
    ;;
esac

script_directory="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
exec python3 "${script_directory}/shared-ci.py" tools \
  --destination "${install_directory}" "${selection[@]}"
