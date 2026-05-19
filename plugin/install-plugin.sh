#!/bin/bash
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
    echo "ERROR: must run as root (use sudo)." >&2
    exit 1
fi

CONFIG_FILE="/etc/eccube-fim/daemon.yaml"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_SRC="$SCRIPT_DIR/EccubeFim"

# ── pre-flight: plugin source must exist ──────────────────────────────────
if [[ ! -d "$PLUGIN_SRC" ]]; then
    echo "ERROR: plugin source not found: $PLUGIN_SRC" >&2
    exit 1
fi

# ── resolve eccube root from daemon config ────────────────────────────────
if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "ERROR: $CONFIG_FILE not found — install the eccube-fim daemon first." >&2
    exit 1
fi

ECCUBE_ROOT=$(python3 -c "import yaml,sys; print(yaml.safe_load(open(sys.argv[1]))['root_path'])" "$CONFIG_FILE" || true)
if [[ -z "$ECCUBE_ROOT" ]]; then
    echo "ERROR: root_path not set in $CONFIG_FILE." >&2
    exit 1
fi

PLUGIN_DST="$ECCUBE_ROOT/app/Plugin/EccubeFim"

# ── pre-flight: verify EC-CUBE root ──────────────────────────────────────
if [[ ! -d "$ECCUBE_ROOT/bin" ]]; then
    echo "ERROR: $ECCUBE_ROOT does not look like an EC-CUBE installation (bin/ missing)." >&2
    exit 1
fi

echo "EC-CUBE root : $ECCUBE_ROOT"
echo "Plugin source: $PLUGIN_SRC"
echo "Plugin dest  : $PLUGIN_DST"
echo ""

# ── copy plugin files ─────────────────────────────────────────────────────
if [[ -d "$PLUGIN_DST" ]]; then
    echo "Updating existing plugin at $PLUGIN_DST ..."
else
    echo "Installing plugin to $PLUGIN_DST ..."
    mkdir -p "$PLUGIN_DST"
fi

trap 'echo "ERROR: copy failed, $PLUGIN_DST may be incomplete." >&2' ERR
cp -r "$PLUGIN_SRC/." "$PLUGIN_DST/"

find "$PLUGIN_DST" -type f -exec chmod 644 {} \;
find "$PLUGIN_DST" -type d -exec chmod 755 {} \;
trap - ERR
echo "Done."
echo ""

# ── next-step instructions ────────────────────────────────────────────────
ADMIN_ROUTE=$(grep -iE '^\s*ECCUBE_ADMIN_ROUTE\s*=' "$ECCUBE_ROOT/.env" 2>/dev/null | sed 's/.*=\s*//' | tr -d '"' || true)
if [[ -z "$ADMIN_ROUTE" ]]; then
    ADMIN_ROUTE="admin"
    echo "(ECCUBE_ADMIN_ROUTE not detected in .env, defaulting to 'admin')"
fi

echo "============================================================"
echo " Plugin files copied. Run the following commands to activate:"
echo "============================================================"
echo ""
echo "  cd $ECCUBE_ROOT"
echo "  php bin/console eccube:plugin:install --code=EccubeFim"
echo "  php bin/console eccube:plugin:enable  --code=EccubeFim"
echo "  php bin/console cache:clear --env=prod --no-warmup"
echo ""
echo "Dashboard URL: https://<your-site>/$ADMIN_ROUTE/fim"
echo ""
