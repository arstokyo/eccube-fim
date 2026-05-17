# ---------------------------------------------------------------------------
# Library + CLI install
# ---------------------------------------------------------------------------
install_library() {
    info "Installing Python library"
    rm -rf "$LIB_DIR/fim"
    cp -R "$SRC_DIR/fim" "$LIB_DIR/fim"
    find "$LIB_DIR" -type d -exec chmod 755 {} \;
    find "$LIB_DIR" -type f -exec chmod 644 {} \;
    chown -R root:root "$LIB_DIR"
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

