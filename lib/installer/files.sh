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

guard_existing_malware_version() {
    [ "$VERSION" = "local" ] && return 0
    malware_installed || return 0
    local installed target
    installed="$(installed_version)"
    target="$(target_version)"
    [ "$installed" = "$target" ] && return 0
    error "Existing eccube-malware installation detected at version ${installed}."
    error "This installer will install eccube-common ${target}; mixed versions are unsafe."
    error "Run first: sudo eccube-malware upgrade"
    error "Then rerun this eccube-fim installer."
    exit 1
}

guard_existing_fim_version() {
    [ "$VERSION" = "local" ] && return 0
    fim_installed || return 0
    local installed target
    installed="$(installed_version)"
    target="$(target_version)"
    [ "$installed" = "$target" ] && return 0
    error "Existing eccube-fim installation detected at version ${installed}."
    error "This installer will install eccube-common ${target}; mixed versions are unsafe."
    error "Run first: sudo eccube-fim upgrade"
    error "Then rerun this eccube-malware installer."
    exit 1
}

# ---------------------------------------------------------------------------
# Library + CLI install
# ---------------------------------------------------------------------------
install_common_library() {
    info "Installing shared Python library"
    mkdir -p "$LIB_DIR"
    rm -rf "$LIB_DIR/common"
    cp -R "$SRC_DIR/common" "$LIB_DIR/common"
    find "$LIB_DIR/common" -type d -exec chmod 755 {} \;
    find "$LIB_DIR/common" -type f -exec chmod 644 {} \;
    chown -R root:root "$LIB_DIR/common"
}

install_fim_library() {
    info "Installing FIM Python library"
    mkdir -p "$LIB_DIR"
    rm -rf "$LIB_DIR/fim"
    cp -R "$SRC_DIR/fim" "$LIB_DIR/fim"
    find "$LIB_DIR/fim" -type d -exec chmod 755 {} \;
    find "$LIB_DIR/fim" -type f -exec chmod 644 {} \;
    chown -R root:root "$LIB_DIR/fim"
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

