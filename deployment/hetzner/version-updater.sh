#!/usr/bin/env bash
set -Eeuo pipefail

umask 077

script_directory="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
deployment_root="$(cd -- "${script_directory}/.." && pwd -P)"
readonly script_directory deployment_root
readonly incoming_directory="${deployment_root}/incoming"
readonly releases_directory="${deployment_root}/releases"
readonly pending_file="${script_directory}/pending-release"
readonly -a managed_links=(current previous-1 previous-2 previous-3 previous-4)

fail() {
  printf 'BoxFerry release update rejected: %s\n' "$1" >&2
  exit 2
}

validate_revision() {
  local revision=$1
  [[ "${revision}" =~ ^[0-9a-f]{40}$ ]] || fail "revision must be 40 lowercase hex digits"
}

validate_target() {
  local target=$1
  [[ "${target}" =~ ^releases/[0-9a-f]{40}$ ]] || fail "managed link target is invalid"
}

ensure_layout() {
  local path
  for path in "${incoming_directory}" "${releases_directory}"; do
    [[ -d "${path}" && ! -L "${path}" ]] || fail "required directory is missing or unsafe: ${path}"
  done
}

read_link_target() {
  local name=$1
  local path="${deployment_root}/${name}"
  local target
  if [[ -L "${path}" ]]; then
    target="$(readlink -- "${path}")"
    validate_target "${target}"
    printf '%s\n' "${target}"
  elif [[ -e "${path}" ]]; then
    fail "managed link path is not a symbolic link: ${name}"
  else
    printf '%s\n' none
  fi
}

replace_link() {
  local name=$1
  local target=$2
  local destination="${deployment_root}/${name}"
  local temporary_directory
  if [[ "${target}" == none ]]; then
    if [[ -L "${destination}" ]]; then
      rm -- "${destination}"
    elif [[ -e "${destination}" ]]; then
      fail "managed link path is not a symbolic link: ${name}"
    fi
    return
  fi

  validate_target "${target}"
  [[ -d "${deployment_root}/${target}" && ! -L "${deployment_root}/${target}" ]] ||
    fail "managed link target does not exist: ${target}"
  temporary_directory="$(mktemp -d "${script_directory}/link.XXXXXX")"
  ln -s -- "${target}" "${temporary_directory}/link"
  mv -Tf -- "${temporary_directory}/link" "${destination}"
  rmdir -- "${temporary_directory}"
}

validate_release_directory() {
  local directory=$1
  local revision=$2
  local manifest="${directory}/.boxferry-release"
  [[ -d "${directory}" && ! -L "${directory}" ]] || fail "release directory is missing or unsafe"
  [[ -f "${manifest}" && ! -L "${manifest}" ]] || fail "release manifest is missing or unsafe"
  [[ "$(wc -l < "${manifest}")" -eq 2 ]] || fail "release manifest has an invalid contract"
  grep -Fxq 'schema-version=1' "${manifest}" || fail "release manifest schema is invalid"
  grep -Fxq "revision=${revision}" "${manifest}" || fail "release manifest revision does not match"
  [[ -f "${directory}/.htaccess" && ! -L "${directory}/.htaccess" ]] ||
    fail "Apache policy is missing or unsafe"
  [[ -f "${directory}/index.html" && ! -L "${directory}/index.html" ]] ||
    fail "site index is missing or unsafe"
  [[ -f "${directory}/docs/index.html" && ! -L "${directory}/docs/index.html" ]] ||
    fail "documentation index is missing or unsafe"
  [[ -f "${directory}/assets/data/deployment.json" &&
    ! -L "${directory}/assets/data/deployment.json" ]] ||
    fail "deployment metadata is missing or unsafe"
  grep -Fq "\"website_revision\": \"${revision}\"" \
    "${directory}/assets/data/deployment.json" ||
    fail "deployment metadata revision does not match"
  [[ -z "$(find "${directory}" -type l -print -quit)" ]] || fail "release contains symbolic links"
}

pending_value() {
  local key=$1
  local count value
  count="$(grep -c "^${key}=" "${pending_file}" || true)"
  [[ "${count}" -eq 1 ]] || fail "pending release state is invalid"
  value="$(sed -n "s/^${key}=//p" "${pending_file}")"
  printf '%s\n' "${value}"
}

load_pending() {
  local expected_revision=$1
  local link
  [[ -f "${pending_file}" && ! -L "${pending_file}" ]] || fail "no pending release exists"
  [[ "$(wc -l < "${pending_file}")" -eq 8 ]] || fail "pending release state is invalid"
  [[ "$(pending_value schema-version)" == 1 ]] || fail "pending release schema is invalid"
  pending_revision="$(pending_value revision)"
  validate_revision "${pending_revision}"
  [[ "${pending_revision}" == "${expected_revision}" ]] || fail "pending revision does not match"
  pending_created="$(pending_value created)"
  [[ "${pending_created}" == yes || "${pending_created}" == no ]] ||
    fail "pending release creation state is invalid"
  declare -gA pending_links=()
  for link in "${managed_links[@]}"; do
    pending_links["${link}"]="$(pending_value "${link}")"
    if [[ "${pending_links[${link}]}" != none ]]; then
      validate_target "${pending_links[${link}]}"
    fi
  done
}

write_pending() {
  local revision=$1
  local created=$2
  shift 2
  local temporary_file
  [[ ! -e "${pending_file}" && ! -L "${pending_file}" ]] ||
    fail "another release is pending finalize or rollback"
  temporary_file="$(mktemp "${script_directory}/pending.XXXXXX")"
  {
    printf 'schema-version=1\n'
    printf 'revision=%s\n' "${revision}"
    printf 'created=%s\n' "${created}"
    printf 'current=%s\n' "$1"
    printf 'previous-1=%s\n' "$2"
    printf 'previous-2=%s\n' "$3"
    printf 'previous-3=%s\n' "$4"
    printf 'previous-4=%s\n' "$5"
  } > "${temporary_file}"
  chmod 600 "${temporary_file}"
  mv -f -- "${temporary_file}" "${pending_file}"
}

target_is_referenced() {
  local expected=$1
  local link
  for link in "${managed_links[@]}"; do
    if [[ "$(read_link_target "${link}")" == "${expected}" ]]; then
      return 0
    fi
  done
  return 1
}

remove_unreferenced_release() {
  local target=$1
  local path
  [[ "${target}" != none ]] || return 0
  validate_target "${target}"
  target_is_referenced "${target}" && return 0
  path="${deployment_root}/${target}"
  if [[ -e "${path}" || -L "${path}" ]]; then
    [[ -d "${path}" && ! -L "${path}" ]] || fail "obsolete release path is unsafe"
    validate_release_directory "${path}" "${target#releases/}"
    rm -rf -- "${path}"
  fi
}

activate_release() {
  local revision=$1
  local staging_name=$2
  local staging_directory release_directory release_target created current_target link
  local -a old_targets=()
  validate_revision "${revision}"
  [[ "${staging_name}" =~ ^${revision}-[0-9]+-[0-9]+$ ]] || fail "staging name is invalid"
  staging_directory="${incoming_directory}/${staging_name}"
  release_directory="${releases_directory}/${revision}"
  release_target="releases/${revision}"
  validate_release_directory "${staging_directory}" "${revision}"

  for link in "${managed_links[@]}"; do
    old_targets+=("$(read_link_target "${link}")")
  done
  current_target="${old_targets[0]}"
  if [[ "${current_target}" == "${release_target}" ]]; then
    if [[ -d "${release_directory}" && ! -L "${release_directory}" ]]; then
      validate_release_directory "${release_directory}" "${revision}"
    else
      fail "current release target is missing"
    fi
    rm -rf -- "${staging_directory}"
    printf 'BoxFerry release %s is already current.\n' "${revision}"
    return
  fi
  for link in "${old_targets[@]:1}"; do
    [[ "${link}" != "${release_target}" ]] || fail "release is already retained in history"
  done

  if [[ -e "${release_directory}" || -L "${release_directory}" ]]; then
    [[ -d "${release_directory}" && ! -L "${release_directory}" ]] ||
      fail "release destination is unsafe"
    validate_release_directory "${release_directory}" "${revision}"
    created=no
  else
    created=yes
  fi
  write_pending "${revision}" "${created}" "${old_targets[@]}"
  if [[ "${created}" == yes ]]; then
    mv -- "${staging_directory}" "${release_directory}"
  else
    rm -rf -- "${staging_directory}"
  fi

  replace_link previous-4 "${old_targets[3]}"
  replace_link previous-3 "${old_targets[2]}"
  replace_link previous-2 "${old_targets[1]}"
  replace_link previous-1 "${old_targets[0]}"
  replace_link current "${release_target}"
  printf 'Activated BoxFerry release %s; verification is required.\n' "${revision}"
}

bootstrap_release() {
  local revision=$1
  local staging_name=$2
  local current_target link target
  local -a targets=()
  validate_revision "${revision}"
  for link in "${managed_links[@]}"; do
    targets+=("$(read_link_target "${link}")")
  done
  current_target="${targets[0]}"
  for target in "${targets[@]:1}"; do
    [[ "${target}" == none ]] || fail "bootstrap requires empty release history"
  done

  if [[ "${current_target}" == none ]]; then
    [[ ! -e "${pending_file}" && ! -L "${pending_file}" ]] ||
      fail "bootstrap requires no pending release"
    [[ -z "$(find "${releases_directory}" -mindepth 1 -maxdepth 1 -print -quit)" ]] ||
      fail "bootstrap requires empty release storage"
  elif [[ "${current_target}" == "releases/${revision}" ]]; then
    [[ -z "$(find "${releases_directory}" -mindepth 1 -maxdepth 1 \
      ! -name "${revision}" -print -quit)" ]] ||
      fail "bootstrap requires exactly one release"
    if [[ -e "${pending_file}" || -L "${pending_file}" ]]; then
      load_pending "${revision}"
      for link in "${managed_links[@]}"; do
        [[ "${pending_links[${link}]}" == none ]] ||
          fail "bootstrap pending state contains release history"
      done
    fi
  else
    fail "bootstrap is permitted only for the first release"
  fi

  activate_release "${revision}" "${staging_name}"
  finalize_release "${revision}"
  printf 'Bootstrapped initial BoxFerry release %s.\n' "${revision}"
}

finalize_release() {
  local revision=$1
  local current_target oldest_link=previous-4
  validate_revision "${revision}"
  current_target="$(read_link_target current)"
  if [[ ! -e "${pending_file}" && ! -L "${pending_file}" ]]; then
    [[ "${current_target}" == "releases/${revision}" ]] || fail "release is not current"
    printf 'BoxFerry release %s is already finalized.\n' "${revision}"
    return
  fi
  load_pending "${revision}"
  [[ "${current_target}" == "releases/${revision}" ]] || fail "pending release is not current"
  remove_unreferenced_release "${pending_links[${oldest_link}]}"
  rm -- "${pending_file}"
  printf 'Finalized BoxFerry release %s.\n' "${revision}"
}

restore_pending_release() {
  local revision=$1
  local link
  load_pending "${revision}"
  for link in "${managed_links[@]}"; do
    replace_link "${link}" "${pending_links[${link}]}"
  done
  if [[ "${pending_created}" == yes ]]; then
    remove_unreferenced_release "releases/${revision}"
  fi
  rm -- "${pending_file}"
  printf 'Rolled back BoxFerry release %s.\n' "${revision}"
}

promote_retained_release() {
  local revision=$1
  local release_target="releases/${revision}"
  local found=false link target
  local -a old_targets=() new_targets=()
  [[ -d "${releases_directory}/${revision}" && ! -L "${releases_directory}/${revision}" ]] ||
    fail "retained release does not exist"
  validate_release_directory "${releases_directory}/${revision}" "${revision}"
  for link in "${managed_links[@]}"; do
    old_targets+=("$(read_link_target "${link}")")
  done
  if [[ "${old_targets[0]}" == "${release_target}" ]]; then
    if [[ -f "${pending_file}" && ! -L "${pending_file}" ]]; then
      load_pending "${revision}"
      printf 'BoxFerry release %s is already promoted; verification is required.\n' "${revision}"
      return
    fi
    fail "release is already current"
  fi
  for target in "${old_targets[@]:1}"; do
    if [[ "${target}" == "${release_target}" ]]; then
      found=true
    fi
  done
  [[ "${found}" == true ]] || fail "release is not retained by a previous link"

  new_targets=("${release_target}" "${old_targets[0]}")
  for target in "${old_targets[@]:1}"; do
    if [[ "${target}" != "${release_target}" ]]; then
      new_targets+=("${target}")
    fi
  done
  while ((${#new_targets[@]} < 5)); do
    new_targets+=(none)
  done

  write_pending "${revision}" no "${old_targets[@]}"
  replace_link previous-4 "${new_targets[4]}"
  replace_link previous-3 "${new_targets[3]}"
  replace_link previous-2 "${new_targets[2]}"
  replace_link previous-1 "${new_targets[1]}"
  replace_link current "${new_targets[0]}"
  printf 'Promoted retained BoxFerry release %s; verification is required.\n' "${revision}"
}

rollback_release() {
  local revision=$1
  local current_target
  validate_revision "${revision}"
  if [[ ! -e "${pending_file}" && ! -L "${pending_file}" ]]; then
    current_target="$(read_link_target current)"
    [[ "${current_target}" == "releases/${revision}" ]] ||
      fail "no pending release exists"
    printf 'BoxFerry release %s has no pending change to roll back.\n' "${revision}"
    return
  fi
  restore_pending_release "${revision}"
}

main() {
  local request operation first second extra
  (($# == 0)) || fail "command-line arguments are not accepted"
  [[ -z "${SSH_ORIGINAL_COMMAND:-}" ]] || fail "SSH command requests are not accepted"
  ensure_layout
  IFS= read -r request || fail "one deployment request is required on standard input"
  if IFS= read -r extra; then
    fail "only one deployment request line is accepted"
  fi
  read -r operation first second extra <<< "${request}"
  [[ -z "${extra:-}" ]] || fail "deployment request has too many fields"
  case "${operation:-}" in
    bootstrap)
      [[ -n "${first:-}" && -n "${second:-}" ]] ||
        fail "bootstrap requires revision and staging name"
      bootstrap_release "${first}" "${second}"
      ;;
    activate)
      [[ -n "${first:-}" && -n "${second:-}" ]] || fail "activate requires revision and staging name"
      activate_release "${first}" "${second}"
      ;;
    finalize)
      [[ -n "${first:-}" && -z "${second:-}" ]] || fail "finalize requires one revision"
      finalize_release "${first}"
      ;;
    promote)
      [[ -n "${first:-}" && -z "${second:-}" ]] || fail "promote requires one revision"
      validate_revision "${first}"
      promote_retained_release "${first}"
      ;;
    rollback)
      [[ -n "${first:-}" && -z "${second:-}" ]] || fail "rollback requires one revision"
      rollback_release "${first}"
      ;;
    *) fail "unknown deployment operation" ;;
  esac
}

main "$@"
