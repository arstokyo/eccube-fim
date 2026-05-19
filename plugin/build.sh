#!/usr/bin/env bash
# Concatenate lib/installer/header.sh + lib/plugin/*.sh → plugin/install-plugin.sh
# Reuses shared repo constants (REPO_SLUG, REPO, RELEASES_API) from header.sh.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$REPO_ROOT/plugin/install-plugin.sh"

{
    # Write plugin-specific header; extract only the 3 shared repo constants from header.sh.
    printf '#!/bin/bash\n'
    printf '# plugin/install-plugin.sh — copy EccubeFim plugin into an existing EC-CUBE installation\n'
    printf '# Run as root after the eccube-fim daemon is installed.\n'
    printf 'set -euo pipefail\n\n'
    grep -E '^(REPO_SLUG=|REPO=|RELEASES_API=)' "$REPO_ROOT/lib/installer/header.sh"
    printf '\n'
    cat "$REPO_ROOT/lib/plugin/common.sh"
    cat "$REPO_ROOT/lib/plugin/main.sh"
} > "$OUT"

chmod +x "$OUT"
echo "Built $OUT ($(wc -l < "$OUT") lines)"
