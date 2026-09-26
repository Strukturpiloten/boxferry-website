#!/usr/bin/env bash

set -Eeuo pipefail

if (($# > 2)); then
  printf 'Usage: %s [install-directory] [--lychee-only]\n' "$0" >&2
  exit 2
fi
readonly install_directory="${1:-/usr/local/bin}"
readonly install_mode="${2:-full}"
if [[ "${install_mode}" != full && "${install_mode}" != --lychee-only ]]; then
  printf 'Usage: %s [install-directory] [--lychee-only]\n' "$0" >&2
  exit 2
fi

# renovate: datasource=github-releases depName=tombi-toml/tombi
readonly tombi_version="1.4.1"
# renovate: datasource=github-releases depName=mvdan/sh
readonly shfmt_version="3.13.1"
# renovate: datasource=github-releases depName=koalaman/shellcheck
readonly shellcheck_version="0.11.0"
# renovate: datasource=github-releases depName=hadolint/hadolint
readonly hadolint_version="2.15.1"
# renovate: datasource=github-releases depName=rhysd/actionlint
readonly actionlint_version="1.7.12"
# renovate: datasource=github-releases depName=lycheeverse/lychee releasePrefix=lychee-v
readonly lychee_version="0.24.2"

case "$(uname -m)" in
  x86_64)
    readonly release_architecture="x86_64"
    readonly actionlint_architecture="amd64"
    readonly shfmt_architecture="amd64"
    readonly tombi_architecture="x86_64-unknown-linux-musl"
    readonly tombi_checksum="9aa69eb3e75a4a22a961b8a1c8cc44e4f81328ce25ad5b10d151be1a09faa88d"
    readonly shfmt_checksum="fb096c5d1ac6beabbdbaa2874d025badb03ee07929f0c9ff67563ce8c75398b1"
    readonly shellcheck_checksum="8c3be12b05d5c177a04c29e3c78ce89ac86f1595681cab149b65b97c4e227198"
    readonly hadolint_checksum="c7187db94eeeeca956519a6af171adc31453941a1e777961f6e680f697c8c507"
    readonly lychee_architecture="x86_64-unknown-linux-gnu"
    readonly lychee_checksum="1f4e0ef7f6554a6ed33dd7ac144fb2e1bbed98598e7af973042fc5cd43951c9a"
    ;;
  aarch64 | arm64)
    readonly release_architecture="aarch64"
    readonly actionlint_architecture="arm64"
    readonly shfmt_architecture="arm64"
    readonly tombi_architecture="aarch64-unknown-linux-musl"
    readonly tombi_checksum="21f51d092597053266e0ed051082743b5956b6de2f0db1cecce78e0eb29165e5"
    readonly shfmt_checksum="32d92acaa5cd8abb29fc49dac123dc412442d5713967819d8af2c29f1b3857c7"
    readonly shellcheck_checksum="12b331c1d2db6b9eb13cfca64306b1b157a86eb69db83023e261eaa7e7c14588"
    readonly hadolint_checksum="f6198ef8090f404dbb771abfee086eb8c48ac177f30da7fd3510aca35b344b5d"
    readonly lychee_architecture="aarch64-unknown-linux-gnu"
    readonly lychee_checksum="91a7bd65685da41b90ccb9bc867a3d649a7818042dae04ff405e55a25bddee4c"
    ;;
  *)
    printf 'Unsupported file-tool architecture: %s\n' "$(uname -m)" >&2
    exit 1
    ;;
esac

temporary_directory="$(mktemp -d)"
readonly temporary_directory
trap 'rm -r -- "${temporary_directory}"' EXIT

download() {
  local url=$1
  local destination=$2
  local checksum=$3

  printf 'Downloading %s\n' "${url##*/}"
  curl --proto '=https' --tlsv1.2 --fail --location --silent --show-error \
    --output "${destination}" "${url}"
  printf '%s  %s\n' "${checksum}" "${destination}" | sha256sum --check --status
}

install -d "${install_directory}"

lychee_archive="${temporary_directory}/lychee.tar.gz"
download \
  "https://github.com/lycheeverse/lychee/releases/download/lychee-v${lychee_version}/lychee-${lychee_architecture}.tar.gz" \
  "${lychee_archive}" "${lychee_checksum}"
tar --extract --gzip --file "${lychee_archive}" --directory "${temporary_directory}" \
  --no-same-owner --no-same-permissions "lychee-${lychee_architecture}/lychee"
lychee_binary="${temporary_directory}/lychee-${lychee_architecture}/lychee"
if [[ ! -f "${lychee_binary}" || -L "${lychee_binary}" ||
  "$("${lychee_binary}" --version)" != "lychee ${lychee_version}" ]]; then
  printf 'Lychee release archive did not contain the expected executable version.\n' >&2
  exit 1
fi
install -m 0755 "${lychee_binary}" "${install_directory}/lychee"

if [[ "${install_mode}" == --lychee-only ]]; then
  printf 'Installed Lychee %s.\n' "${lychee_version}"
  exit 0
fi

tombi_archive="${temporary_directory}/tombi.tar.gz"
download \
  "https://github.com/tombi-toml/tombi/releases/download/v${tombi_version}/tombi-cli-${tombi_version}-${tombi_architecture}.tar.gz" \
  "${tombi_archive}" "${tombi_checksum}"
tar --extract --gzip --file "${tombi_archive}" --directory "${temporary_directory}"
install -m 0755 \
  "${temporary_directory}/tombi-cli-${tombi_version}-${tombi_architecture}/tombi" \
  "${install_directory}/tombi"

shfmt_binary="${temporary_directory}/shfmt"
download \
  "https://github.com/mvdan/sh/releases/download/v${shfmt_version}/shfmt_v${shfmt_version}_linux_${shfmt_architecture}" \
  "${shfmt_binary}" "${shfmt_checksum}"
install -m 0755 "${shfmt_binary}" "${install_directory}/shfmt"

shellcheck_archive="${temporary_directory}/shellcheck.tar.xz"
download \
  "https://github.com/koalaman/shellcheck/releases/download/v${shellcheck_version}/shellcheck-v${shellcheck_version}.linux.${release_architecture}.tar.xz" \
  "${shellcheck_archive}" "${shellcheck_checksum}"
tar --extract --xz --file "${shellcheck_archive}" --directory "${temporary_directory}"
install -m 0755 \
  "${temporary_directory}/shellcheck-v${shellcheck_version}/shellcheck" \
  "${install_directory}/shellcheck"

hadolint_binary="${temporary_directory}/hadolint"
download \
  "https://github.com/hadolint/hadolint/releases/download/v${hadolint_version}/hadolint-linux-${release_architecture}" \
  "${hadolint_binary}" "${hadolint_checksum}"
install -m 0755 "${hadolint_binary}" "${install_directory}/hadolint"

actionlint_release_url="https://github.com/rhysd/actionlint/releases/download/v${actionlint_version}"
actionlint_archive="actionlint_${actionlint_version}_linux_${actionlint_architecture}.tar.gz"
curl --proto '=https' --tlsv1.2 --fail --location --silent --show-error \
  --output "${temporary_directory}/actionlint-checksums.txt" \
  "${actionlint_release_url}/actionlint_${actionlint_version}_checksums.txt"
curl --proto '=https' --tlsv1.2 --fail --location --silent --show-error \
  --output "${temporary_directory}/${actionlint_archive}" \
  "${actionlint_release_url}/${actionlint_archive}"
actionlint_checksum="$(
  grep -F "  ${actionlint_archive}" "${temporary_directory}/actionlint-checksums.txt" |
    cut --delimiter=' ' --fields=1
)"
if [[ -z "${actionlint_checksum}" ]]; then
  printf 'Actionlint checksum is missing for %s.\n' "${actionlint_archive}" >&2
  exit 1
fi
printf '%s  %s\n' "${actionlint_checksum}" "${temporary_directory}/${actionlint_archive}" |
  sha256sum --check --status
tar --extract --gzip --file "${temporary_directory}/${actionlint_archive}" \
  --directory "${temporary_directory}" actionlint
install -m 0755 "${temporary_directory}/actionlint" "${install_directory}/actionlint"

printf 'Installed Lychee %s, Tombi %s, shfmt %s, ShellCheck %s, Hadolint %s, and actionlint %s.\n' \
  "${lychee_version}" \
  "${tombi_version}" "${shfmt_version}" "${shellcheck_version}" "${hadolint_version}" \
  "${actionlint_version}"
