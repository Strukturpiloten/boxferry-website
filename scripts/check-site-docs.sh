#!/usr/bin/env bash

set -Eeuo pipefail

script_directory="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repository_root="$(cd -- "${script_directory}/.." && pwd -P)"
cd -- "${repository_root}"

if [[ "${BOXFERRY_WEBSITE_SHARED_TOOLS:-}" != 1 ]]; then
  exec python3 "${repository_root}/scripts/shared-ci.py" run --task site-docs \
    --report-json "${repository_root}/target/site-docs.json"
fi

source_mode="${BOXFERRY_WEBSITE_SOURCE_MODE:-local}"
case "${source_mode}" in
  local | locked) ;;
  *)
    printf 'BOXFERRY_WEBSITE_SOURCE_MODE must be local or locked\n' >&2
    exit 2
    ;;
esac

npm ci --ignore-scripts
export PATH="${repository_root}/node_modules/.bin:${PATH}"
uv sync --locked

markdown_inventory="$(mktemp)"
trap 'rm -f -- "${markdown_inventory}"' EXIT
git ls-files --cached --others --exclude-standard -z -- '*.md' > "${markdown_inventory}"

markdown_files=()
source_links=()
while IFS= read -r -d '' markdown_file; do
  if [[ -f "${markdown_file}" ]]; then
    markdown_files+=("${markdown_file}")
    # The homepage links to assembled public routes, checked by the strict build.
    if [[ "${markdown_file}" != content/index.md ]]; then
      source_links+=("${markdown_file}")
    fi
  fi
done < "${markdown_inventory}"
if ((${#markdown_files[@]} == 0)); then
  printf 'No owned Markdown documents found.\n' >&2
  exit 2
fi

prettier --check --ignore-path .prettierignore --ignore-unknown "${markdown_files[@]}"
markdownlint-cli2 "${markdown_files[@]/#/:}"
cspell --config cspell.json --no-progress --no-summary -- "${markdown_files[@]}"
lychee --config lychee.toml --root-dir . --offline "${source_links[@]}"
uv run --frozen python scripts/assemble_docs.py --source-mode "${source_mode}"
uv run --frozen zensical build --clean --strict
uv run --frozen python scripts/publish_ai_docs.py
git --no-pager diff --check
