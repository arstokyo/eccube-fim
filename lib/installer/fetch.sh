# ---------------------------------------------------------------------------
# Source fetch — latest GitHub Release only; errors on network failure
# ---------------------------------------------------------------------------
_fetch_release_info() {
    local response
    response=$(curl -fsSL "$RELEASES_API" 2>/dev/null) || true
    VERSION=$(echo "$response" | grep '"tag_name"' | cut -d'"' -f4)
    if [ -z "$VERSION" ]; then
        error "Could not resolve latest release."
        error "Check your network or visit: https://github.com/${REPO_SLUG}/releases"
        exit 1
    fi
    PYTHON_REQUIRES=$(echo "$response" | python3 -c "
import json, sys, re
try:
    data = json.load(sys.stdin)
    body = data.get('body', '')
    m = re.search(r'python_requires:\s*\"(.*?)\"', body)
    print(m.group(1) if m else '')
except Exception:
    print('')
" 2>/dev/null || echo "")
}

_check_python_requires() {
    local requires="$1"
    [ -z "$requires" ] && return
    python3 -c "
import sys, re
requires = '${requires}'
min_ver = tuple(int(x) for x in re.sub(r'^[>=]+', '', requires).split('.'))
actual  = sys.version_info[:len(min_ver)]
if actual < min_ver:
    needed  = '.'.join(str(x) for x in min_ver)
    running = f'{sys.version_info.major}.{sys.version_info.minor}'
    print(f'ERROR: This release requires Python {needed}+ (found Python {running}).',
          file=sys.stderr)
    print('You are already on the latest version compatible with your Python.',
          file=sys.stderr)
    sys.exit(1)
" || exit 1
}

_download_release_asset() {
    local asset_name="$1"
    local dest_dir="$2"
    local url="${REPO}/releases/download/${VERSION}/${asset_name}"
    info "Downloading ${asset_name}..."
    if ! curl -fsSL "$url" | tar xz --strip-components=1 -C "$dest_dir"; then
        error "Download failed: ${asset_name}"
        error "Check the release assets: ${REPO}/releases/tag/${VERSION}"
        exit 1
    fi
}

_prepare_release_source_dir() {
    SRC_DIR="$(mktemp -d)"
    # shellcheck disable=SC2064
    # double-quoted: bake in SRC_DIR now so EXIT cleanup still has the path
    trap "rm -rf '$SRC_DIR'" EXIT
}

fetch_source() {
    local script_dir
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]:-}")" 2>/dev/null && pwd || echo "")"
    if [ -d "${script_dir}/fim" ] && [ -d "${script_dir}/common" ]; then
        SRC_DIR="$script_dir"
        VERSION="local"
        info "Using local source: $SRC_DIR"
        return
    fi
    _fetch_release_info
    _check_python_requires "$PYTHON_REQUIRES"
    _prepare_release_source_dir
    _download_release_asset "eccube-common-${VERSION}.tar.gz" "$SRC_DIR"
    _download_release_asset "eccube-fim-${VERSION}.tar.gz" "$SRC_DIR"
    info "Source ready: eccube-fim ${VERSION}"
}

