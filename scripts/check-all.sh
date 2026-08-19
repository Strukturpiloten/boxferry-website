#!/usr/bin/env bash

set -Eeuo pipefail

script_directory="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repository_root="$(cd -- "${script_directory}/.." && pwd -P)"
readonly repository_root

cd -- "${repository_root}"

current_step="preflight"
step=0
readonly total_steps=15

fail() {
  printf 'BoxFerry website local validation failed: %s\n' "$1" >&2
  exit 2
}

report_failure() {
  local status=$?
  printf '\nBoxFerry website local validation failed during: %s (exit %d)\n' \
    "${current_step}" "${status}" >&2
  exit "${status}"
}

trap report_failure ERR

format_mode="${BOXFERRY_WEBSITE_FORMAT_MODE:-fix}"
case "${format_mode}" in
  check | fix) ;;
  *) fail "BOXFERRY_WEBSITE_FORMAT_MODE must be check or fix" ;;
esac
readonly format_mode

source_mode="${BOXFERRY_WEBSITE_SOURCE_MODE:-local}"
case "${source_mode}" in
  local | locked) ;;
  *) fail "BOXFERRY_WEBSITE_SOURCE_MODE must be local or locked" ;;
esac
readonly source_mode

bootstrap_tools=(git npm uv)
for tool in "${bootstrap_tools[@]}"; do
  command -v "${tool}" > /dev/null 2>&1 || fail "missing required tool: ${tool}"
done

export PATH="${repository_root}/node_modules/.bin:${PATH}"

run_step() {
  local label=$1
  shift
  step=$((step + 1))
  current_step="${label}"
  printf '\n[%02d/%02d] %s\n  +' "${step}" "${total_steps}" "${label}"
  printf ' %q' "$@"
  printf '\n'
  "$@"
}

run_step "Install locked repository tools" npm ci --ignore-scripts
run_step "Synchronize the locked Python environment" uv sync --locked

required_tools=(actionlint git hadolint jq lychee markdownlint-cli2 prettier shellcheck shfmt tombi)
missing_tools=()
for tool in "${required_tools[@]}"; do
  if ! command -v "${tool}" > /dev/null 2>&1; then
    missing_tools+=("${tool}")
  fi
done
if ((${#missing_tools[@]} != 0)); then
  printf -v missing_list ' %s' "${missing_tools[@]}"
  fail "missing required tool(s):${missing_list}. Use the BoxFerry Dev Container."
fi

if [[ "${format_mode}" == "fix" ]]; then
  run_step "Format Python" uv run --frozen ruff format scripts tests
  file_mode="--fix"
else
  run_step "Check Python formatting" uv run --frozen ruff format --check scripts tests
  file_mode="--check"
fi
readonly file_mode

run_step "Format and lint non-Python files" bash scripts/check-files.sh "${file_mode}"
run_step "Check whitespace errors" git --no-pager diff --check
run_step "Lint GitHub Actions syntax" actionlint
run_step "Audit GitHub Actions security" uv run --frozen zizmor .github/workflows
run_step "Check locked dependency resolution" uv lock --check
run_step "Lint Python" uv run --frozen ruff check scripts tests
run_step "Run repository tests" uv run --frozen python -m unittest discover -s tests -v
run_step "Assemble documentation" uv run --frozen python scripts/assemble_docs.py \
  --source-mode "${source_mode}"
run_step "Build the static site with warnings denied" uv run --frozen zensical build --clean --strict
run_step "Verify public routes and privacy boundaries" uv run --frozen python scripts/verify_site.py

mapfile -d '' markdown_files < <(
  git ls-files --cached --others --exclude-standard -z -- '*.md'
)
run_step "Check local source links" lychee --config lychee.toml --root-dir . --offline \
  "${markdown_files[@]}"

cd -- site
mapfile -d '' html_files < <(find . -type f -name '*.html' -print0 | sort -z)
run_step "Check generated site links" lychee --config ../lychee.toml --root-dir . --offline \
  "${html_files[@]}"
cd -- "${repository_root}"

printf '\nBoxFerry website local validation passed all %d steps.\n' "${total_steps}"
