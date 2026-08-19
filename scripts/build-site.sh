#!/usr/bin/env bash

set -Eeuo pipefail

script_directory="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repository_root="$(cd -- "${script_directory}/.." && pwd -P)"
readonly repository_root

source_mode="${BOXFERRY_WEBSITE_SOURCE_MODE:-local}"
case "${source_mode}" in
  local | locked) ;;
  *)
    printf 'BOXFERRY_WEBSITE_SOURCE_MODE must be local or locked\n' >&2
    exit 2
    ;;
esac

cd -- "${repository_root}"
uv sync --locked
uv run --frozen python scripts/assemble_docs.py --source-mode "${source_mode}"
uv run --frozen zensical build --clean --strict
uv run --frozen python scripts/build_rustdoc.py --source-mode "${source_mode}"
