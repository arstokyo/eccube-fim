# ---------------------------------------------------------------------------
# Update mode — refresh code + units, preserve config
# ---------------------------------------------------------------------------
update_mode() {
    local daemon_f="$CONFIG_DIR/daemon.yaml"
    [ -f "$daemon_f" ] || { error "No config found — run without --update for a fresh install"; exit 1; }
    install_library
    install_cli
    install_logrotate
    ECCUBE_ROOT=$(awk '/^root_path:/{print $2}' "$daemon_f")
    _read_interval_from_timer
    install_systemd_files
    systemctl restart eccube-fim-check.timer
}

# ---------------------------------------------------------------------------
# Post-install verification offer
# ---------------------------------------------------------------------------
post_install_checks() {
    echo
    local fim_cmd="$SBIN_DIR/eccube-fim"

    if [ "$NONINTERACTIVE" -eq 1 ]; then
        info "Next: $fim_cmd validate"
        info "Next: $fim_cmd test-mail"
        info "Finished."
        return
    fi

    # empty Enter → variable is "", which is != "n", so default is Y
    local run_validate

    if [ ! -x "$fim_cmd" ]; then
        warn "$fim_cmd not found or not executable — run validate/test-mail manually after fixing install"
        info "Finished."
        return
    fi

    read -rp "Run '$fim_cmd validate' now? [Y/n]: " run_validate </dev/tty
    if [ "${run_validate,,}" != "n" ]; then
        echo
        if "$fim_cmd" validate </dev/null; then
            local run_testmail
            read -rp "Send test email via '$fim_cmd test-mail' now? [Y/n]: " run_testmail </dev/tty
            if [ "${run_testmail,,}" != "n" ]; then
                echo
                "$fim_cmd" test-mail </dev/null || warn "test-mail failed — check notify.yaml and SMTP credentials"
            fi
        else
            warn "validate failed — fix config before running test-mail"
        fi
    fi

    echo
    info "Finished."
    return 0
}

