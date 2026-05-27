#!/usr/bin/env bash
# Concatenate lib/installer/*.sh into install.sh in dependency order.
set -euo pipefail

OUT="install.sh"

cat \
    lib/installer/header.sh \
    lib/installer/helpers.sh \
    lib/installer/fetch.sh \
    lib/installer/packages.sh \
    lib/installer/files.sh \
    lib/installer/wizard.sh \
    lib/installer/git.sh \
    lib/installer/systemd.sh \
    lib/installer/lifecycle.sh \
    lib/installer/main.sh \
    > "$OUT"

chmod +x "$OUT"
echo "Built $OUT ($(wc -l < "$OUT") lines)"

# --- install-malware.sh ---
MALWARE_OUT="install-malware.sh"

cat \
    lib/installer/header.sh \
    lib/installer/helpers.sh \
    lib/installer/fetch.sh \
    lib/installer/malware.sh \
    lib/installer/malware_entry.sh \
    > "$MALWARE_OUT"

chmod +x "$MALWARE_OUT"
echo "Built $MALWARE_OUT ($(wc -l < "$MALWARE_OUT") lines)"
