#!/usr/bin/env bash
set -eou pipefail

make_check::run() {
  declare target="${1:-check}"
  local dir

  for dir in */; do
    make_check::check_dir "${dir%/}" "$target"
  done
}

make_check::check_dir() {
  declare dir="$1"
  declare target="$2"
  printf '📂 Entering %s — running `make %s`\n' "$dir" "$target"

  if [[ -d "$dir" ]]; then
    (
      cd "$dir"
      if [[ -f Makefile || -f makefile ]]; then
        make "$target" || {
          printf '❌ make %s failed in %s\n' "$target" "$dir" >&2
          return 1
        }
      else
        printf '⚠️ No Makefile in %s, skipping.\n' "$dir" >&2
      fi
    )
  fi
}

main() {
  make_check::run "${1:-check}"
}

main "$@"
