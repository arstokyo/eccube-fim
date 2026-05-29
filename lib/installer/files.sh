# ---------------------------------------------------------------------------
# Companion version guard helpers
# ---------------------------------------------------------------------------
installed_version() {
    local stamp="${CONFIG_DIR}/.version"
    if [ ! -f "$stamp" ]; then
        # No stamp means companion was installed before plan-082 introduced the stamp.
        # Read __version__ from the companion Python module as a fallback so the
        # version guard can still compare correctly.
        local ver
        ver=$(python3 -c "
import sys
sys.path.insert(0, '${LIB_DIR}')
try:
    from common.version import __version__; print(__version__)
except Exception:
    print('unknown')
" 2>/dev/null)
        echo "$ver"
        return
    fi
    tr -d '[:space:]' < "$stamp"
}

target_version() {
    echo "${VERSION#v}"
}

fim_installed() {
    [ -d "${LIB_DIR}/fim" ] || [ -x "${SBIN_DIR}/eccube-fim" ]
}

malware_installed() {
    [ -d "${LIB_DIR}/malware" ] || [ -x "${SBIN_DIR}/eccube-malware" ]
}

# Generic version guard — called by guard_existing_fim_version(), guard_existing_malware_version()
guard_existing_version() {
    local module="$1" bin_name="$2"
    [ "$VERSION" = "local" ] && return 0
    case "$module" in
        fim)     fim_installed     || return 0 ;;
        malware) malware_installed || return 0 ;;
        *)       error "guard_existing_version: unknown module '$module'"; exit 1 ;;
    esac
    local installed target
    installed="$(installed_version)"
    target="$(target_version)"
    [ "$installed" = "$target" ] && return 0
    error "Existing $bin_name installation detected at version ${installed}."
    error "This installer will install eccube-common ${target}; mixed versions are unsafe."
    error "Run first: sudo $bin_name upgrade"
    error "Then rerun this installer."
    exit 1
}

guard_existing_malware_version() {
    guard_existing_version "malware" "eccube-malware"
}

guard_existing_fim_version() {
    guard_existing_version "fim" "eccube-fim"
}

# ---------------------------------------------------------------------------
# Library + CLI install
# ---------------------------------------------------------------------------
# Generic library installer — called by install_common_library(), install_fim_library(), install_malware_library()
install_library_module() {
    local module="$1"
    [ -n "$module" ] || { error "install_library_module: module name required"; exit 1; }
    info "Installing $module Python library"
    mkdir -p "$LIB_DIR"
    rm -rf "$LIB_DIR/$module"
    cp -r "$SRC_DIR/$module" "$LIB_DIR/$module"
    find "$LIB_DIR/$module" -type d -exec chmod 755 {} \;
    find "$LIB_DIR/$module" -type f -exec chmod 644 {} \;
    chown -R root:root "$LIB_DIR/$module"
}

install_common_library() {
    install_library_module "common"
}

install_fim_library() {
    install_library_module "fim"
}

install_library() {
    install_common_library
    install_fim_library
}

install_version_stamp() {
    info "Writing version stamp (${VERSION#v})"
    printf '%s\n' "${VERSION#v}" > "$CONFIG_DIR/.version"
    chmod 644 "$CONFIG_DIR/.version"
    chown root:root "$CONFIG_DIR/.version"
}

install_cli() {
    info "Installing unified CLI"
    install -m 755 -o root -g root "$SRC_DIR/bin/eccube-fim" "$SBIN_DIR/eccube-fim"
}

install_logrotate() {
    info "Installing logrotate config"
    install -m 644 -o root -g root "$SRC_DIR/eccube-fim.logrotate" /etc/logrotate.d/eccube-fim
}

