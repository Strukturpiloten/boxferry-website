#!/usr/bin/env bash

set -Eeuo pipefail

script_directory="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repository_root="$(cd -- "${script_directory}/.." && pwd -P)"
cd -- "${repository_root}"

# The classifier owns this inventory. Changes to either script select the
# complete PR gate, so a PR cannot change its own policy and qualify as prose.
mapfile -d '' maintenance_docs < <(python3 scripts/validation-plan.py --list-docs)

npm ci --ignore-scripts
export PATH="${repository_root}/node_modules/.bin:${PATH}"
prettier --check --ignore-path .prettierignore --ignore-unknown "${maintenance_docs[@]}"
markdownlint-cli2 "${maintenance_docs[@]/#/:}"
cspell --config cspell.json --no-progress --no-summary -- "${maintenance_docs[@]}"
lychee --config lychee.toml --root-dir . --offline "${maintenance_docs[@]}"
git --no-pager diff --check
