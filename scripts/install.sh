#!/bin/sh
set -eu

usage() {
  echo "Usage: $0 [--backup-existing] [--home PATH]" >&2
  exit 2
}

backup_existing=false
target_home=${AGENT_SETUP_HOME:-$HOME}
while [ "$#" -gt 0 ]; do
  case "$1" in
    --backup-existing) backup_existing=true ;;
    --home)
      [ "$#" -ge 2 ] || usage
      target_home=$2
      shift
      ;;
    *) usage ;;
  esac
  shift
done

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
source_file=$(CDPATH= cd -- "$script_dir/../profiles" && pwd)/signal.md
claude_target=$target_home/.claude/output-styles/signal.md
codex_target=$target_home/.codex/AGENTS.md

is_installed() {
  [ -L "$1" ] && [ "$(readlink "$1")" = "$source_file" ]
}

# Check both targets before changing either one.
for target in "$claude_target" "$codex_target"; do
  if [ -e "$target" ] || [ -L "$target" ]; then
    if ! is_installed "$target" && [ "$backup_existing" = false ]; then
      echo "Existing file: $target (rerun with --backup-existing)" >&2
      exit 1
    fi
  fi
done

for target in "$claude_target" "$codex_target"; do
  if is_installed "$target"; then
    echo "Already linked: $target"
    continue
  fi

  mkdir -p "$(dirname "$target")"
  if [ -e "$target" ] || [ -L "$target" ]; then
    backup=$target.backup.$(date +%Y%m%d%H%M%S).$$
    mv "$target" "$backup"
    echo "Backed up: $backup"
  fi
  ln -s "$source_file" "$target"
  echo "Linked: $target -> $source_file"
done
