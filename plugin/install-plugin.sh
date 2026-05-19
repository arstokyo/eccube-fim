#!/bin/bash
# plugin/install-plugin.sh — copy EccubeFim plugin into an existing EC-CUBE installation
# Run as root after the eccube-fim daemon is installed.
set -euo pipefail

REPO_SLUG="arstokyo/eccube-fim"
REPO="https://github.com/${REPO_SLUG}"
RELEASES_API="https://api.github.com/repos/${REPO_SLUG}/releases/latest"


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
info()  { echo -e "\033[32m[INFO]\033[0m  $*"; }
warn()  { echo -e "\033[33m[WARN]\033[0m  $*"; }
error() { echo -e "\033[31m[ERROR]\033[0m $*" >&2; }

# ---------------------------------------------------------------------------
# Release fetch — extends the base pattern to also resolve the plugin asset URL
# ---------------------------------------------------------------------------
PLUGIN_ASSET_URL=""   # set by _fetch_release_info()
VERSION=""

_fetch_release_info() {
    local response
    response=$(curl -fsSL "$RELEASES_API" 2>/dev/null) || true
    VERSION=$(echo "$response" | grep '"tag_name"' | cut -d'"' -f4)
    if [[ -z "$VERSION" ]]; then
        error "Could not resolve latest release."
        error "Check your network or visit: https://github.com/${REPO_SLUG}/releases"
        exit 1
    fi
    PLUGIN_ASSET_URL=$(echo "$response" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    for a in data.get('assets', []):
        if a['name'].startswith('eccube-fim-plugin-'):
            print(a['browser_download_url'])
            break
except Exception:
    pass
" 2>/dev/null || echo "")
}


# ---------------------------------------------------------------------------
# Plugin installer
# ---------------------------------------------------------------------------
CONFIG_FILE="/etc/eccube-fim/daemon.yaml"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-}")" 2>/dev/null && pwd || echo ".")"
PLUGIN_SRC=""   # set by fetch_plugin_source()

# ── root guard ────────────────────────────────────────────────────────────────
if [[ $EUID -ne 0 ]]; then
    error "must run as root (use sudo)."
    exit 1
fi

fetch_plugin_source() {
    # Local / dev path: EccubeFim/ sits next to this script (repo clone or local run).
    if [[ -d "${SCRIPT_DIR}/EccubeFim" ]]; then
        PLUGIN_SRC="${SCRIPT_DIR}/EccubeFim"
        VERSION="local"
        info "Using local source: $PLUGIN_SRC"
        return
    fi

    _fetch_release_info

    if [[ -z "$PLUGIN_ASSET_URL" ]]; then
        error "Plugin asset not found in release ${VERSION} — no eccube-fim-plugin-* asset attached."
        error "Visit: https://github.com/${REPO_SLUG}/releases/tag/${VERSION}"
        exit 1
    fi

    info "Downloading eccube-fim plugin (${VERSION})..."
    local tmp_dir
    tmp_dir="$(mktemp -d)"
    # double-quoted: bake in path now — tmp_dir is local and out of scope at EXIT
    # shellcheck disable=SC2064
    trap "rm -rf '$tmp_dir'" EXIT
    if ! curl -fsSL "$PLUGIN_ASSET_URL" | tar xz -C "$tmp_dir"; then
        error "Download failed — check your network or visit: https://github.com/${REPO_SLUG}/releases"
        exit 1
    fi
    PLUGIN_SRC="${tmp_dir}/EccubeFim"
    if [[ ! -d "$PLUGIN_SRC" ]]; then
        error "EccubeFim/ not found in plugin tarball (${VERSION})."
        exit 1
    fi
    info "Source ready: eccube-fim plugin ${VERSION}"
}

# ── fetch plugin source (local or remote) ────────────────────────────────────
fetch_plugin_source

# ── resolve eccube root from daemon config ────────────────────────────────────
if [[ ! -f "$CONFIG_FILE" ]]; then
    error "$CONFIG_FILE not found — install the eccube-fim daemon first."
    exit 1
fi

ECCUBE_ROOT=$(python3 -c "import yaml,sys; print(yaml.safe_load(open(sys.argv[1]))['root_path'])" "$CONFIG_FILE" || true)
if [[ -z "$ECCUBE_ROOT" ]]; then
    error "root_path not set in $CONFIG_FILE."
    exit 1
fi

PLUGIN_DST="$ECCUBE_ROOT/app/Plugin/EccubeFim"

# ── pre-flight: verify EC-CUBE root ──────────────────────────────────────────
if [[ ! -d "$ECCUBE_ROOT/bin" ]]; then
    error "$ECCUBE_ROOT does not look like an EC-CUBE installation (bin/ missing)."
    exit 1
fi

echo "EC-CUBE root : $ECCUBE_ROOT"
echo "Plugin source: $PLUGIN_SRC"
echo "Plugin dest  : $PLUGIN_DST"
echo ""

# ── copy plugin files ─────────────────────────────────────────────────────────
if [[ -d "$PLUGIN_DST" ]]; then
    echo "Updating existing plugin at $PLUGIN_DST ..."
else
    echo "Installing plugin to $PLUGIN_DST ..."
    mkdir -p "$PLUGIN_DST"
fi

trap 'error "copy failed, $PLUGIN_DST may be incomplete."' ERR
cp -r "$PLUGIN_SRC/." "$PLUGIN_DST/"
find "$PLUGIN_DST" -type f -exec chmod 644 {} \;
find "$PLUGIN_DST" -type d -exec chmod 755 {} \;
trap - ERR
echo "Done."
echo ""

# ── next-step instructions ────────────────────────────────────────────────────
ADMIN_ROUTE=$(grep -iE '^\s*ECCUBE_ADMIN_ROUTE\s*=' "$ECCUBE_ROOT/.env" 2>/dev/null \
    | sed 's/.*=\s*//' | tr -d '"' || true)
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
