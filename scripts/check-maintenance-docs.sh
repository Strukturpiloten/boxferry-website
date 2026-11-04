#!/usr/bin/env bash

set -Eeuo pipefail

script_directory="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repository_root="$(cd -- "${script_directory}/.." && pwd -P)"
cd -- "${repository_root}"

if [[ "${BOXFERRY_WEBSITE_SHARED_TOOLS:-}" != 1 ]]; then
  exec python3 "${repository_root}/scripts/shared-ci.py" run --task maintenance \
    --report-json "${repository_root}/target/maintenance.json"
fi

# The shared trusted policy owns this exact inventory.
markdown_inventory="$(mktemp)"
trap 'rm -f -- "${markdown_inventory}"' EXIT
python3 - > "${markdown_inventory}" << 'PYTHON'
import json
import sys

with open("scripts/validation-policy.json", encoding="utf-8") as policy_file:
    policy = json.load(policy_file)
sys.stdout.buffer.write(
    b"\0".join(path.encode() for path in policy["path_profiles"]["prose"]) + b"\0"
)
PYTHON
mapfile -d '' maintenance_docs < "${markdown_inventory}"
if ((${#maintenance_docs[@]} == 0)); then
  printf 'No maintenance documents declared by policy.\n' >&2
  exit 2
fi

npm ci --ignore-scripts
export PATH="${repository_root}/node_modules/.bin:${PATH}"
prettier --check --ignore-path .prettierignore --ignore-unknown "${maintenance_docs[@]}"
markdownlint-cli2 "${maintenance_docs[@]/#/:}"
cspell --config cspell.json --no-progress --no-summary -- "${maintenance_docs[@]}"
lychee --config lychee.toml --root-dir . --offline "${maintenance_docs[@]}"
git --no-pager diff --check
