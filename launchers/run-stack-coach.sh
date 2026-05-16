#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

add_path_entry() {
  local candidate="$1"
  if [[ -d "${candidate}" && ":${PATH}:" != *":${candidate}:"* ]]; then
    PATH="${candidate}:${PATH}"
  fi
}

add_path_entry "${HOME}/.local/bin"
add_path_entry "${HOME}/bin"
add_path_entry "/snap/bin"

if [[ -d "${HOME}/.nvm/versions/node" ]]; then
  latest_node_bin="$(
    find "${HOME}/.nvm/versions/node" -mindepth 2 -maxdepth 2 -type d -name bin \
      | sort -V \
      | tail -n 1
  )"
  if [[ -n "${latest_node_bin}" ]]; then
    add_path_entry "${latest_node_bin}"
  fi
fi

export PATH

cd "${repo_root}"
if [[ "${1:-}" == "--browser" ]]; then
  shift
  PYTHONPATH="${repo_root}/src" exec python3 -m stack_review_coach --browser "$@"
fi

PYTHONPATH="${repo_root}/src" exec python3 -m stack_review_coach "$@"
