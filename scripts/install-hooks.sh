#!/usr/bin/env bash
# One-time setup: symlink project hooks into .git/hooks/.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

shopt -s nullglob
for hook in "$REPO_ROOT/hooks/"*; do
    name="$(basename "$hook")"
    target="$REPO_ROOT/.git/hooks/$name"
    ln -sf "../../hooks/$name" "$target"
    echo "Installed: .git/hooks/$name -> hooks/$name"
done
