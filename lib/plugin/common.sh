
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

