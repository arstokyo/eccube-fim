# ---------------------------------------------------------------------------
# systemd units — template substitution
# ---------------------------------------------------------------------------
install_systemd_files() {
    info "Installing systemd units (interval: ${CHECK_INTERVAL}m, root: $ECCUBE_ROOT)"
    sed "s|%%ECCUBE_ROOT%%|${ECCUBE_ROOT}|g" \
        "$SRC_DIR/systemd/eccube-fim-check.service" \
        > /etc/systemd/system/eccube-fim-check.service
    sed "s|%%INTERVAL%%|${CHECK_INTERVAL}|g" \
        "$SRC_DIR/systemd/eccube-fim-check.timer" \
        > /etc/systemd/system/eccube-fim-check.timer
    chmod 644 /etc/systemd/system/eccube-fim-check.service \
              /etc/systemd/system/eccube-fim-check.timer
    systemctl daemon-reload
}

activate_systemd_units() {
    systemctl enable --now eccube-fim-check.timer
}

