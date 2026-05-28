# ---------------------------------------------------------------------------
# Force-retry mode — run migrations only; code already installed on disk
# ---------------------------------------------------------------------------
migrate_only_mode() {
    # Retry path after a failed --update: skip re-download and jump straight to migrations.
    local daemon_f="$CONFIG_DIR/daemon.yaml"
    [ -f "$daemon_f" ] || { error "No config found — run without --update for a fresh install"; exit 1; }
    info "Force-retry: running migrations only (code already installed)"
    "$SBIN_DIR/eccube-fim" _migrate --config-dir "$CONFIG_DIR" || {
        error "Migrations still failing — fix the error above, then retry."
        error "Manual path: $SBIN_DIR/eccube-fim _migrate --config-dir $CONFIG_DIR"
        exit 1
    }
    install_version_stamp
    ECCUBE_ROOT=$(awk '/^root_path:/{print $2}' "$daemon_f")
    _read_interval_from_timer
    install_systemd_files
    systemctl restart eccube-fim-check.timer
    info "Force-retry complete"
}

# ---------------------------------------------------------------------------
# Update mode — refresh code + units, preserve config
# ---------------------------------------------------------------------------
update_mode() {
    local daemon_f="$CONFIG_DIR/daemon.yaml"
    [ -f "$daemon_f" ] || { error "No config found — run without --update for a fresh install"; exit 1; }
    guard_existing_malware_version
    install_common_library
    install_fim_library
    install_cli
    install_logrotate
    # run after new lib + binary are in place so new migration files are used
    "$SBIN_DIR/eccube-fim" _migrate --config-dir "$CONFIG_DIR" || {
        error "Migrations failed — upgrade aborted"
        error "To retry migrations without reinstalling: $SBIN_DIR/eccube-fim upgrade --migrate-only"
        error "To retry manually: $SBIN_DIR/eccube-fim _migrate --config-dir $CONFIG_DIR"
        exit 1
    }
    # stamp written only after migrations succeed so a failed upgrade is retryable
    install_version_stamp
    # belt-and-suspenders: LogsDirectory handles this on service start, but update_mode
    # runs before the service restarts so old installs without LogsDirectory still get the dir
    mkdir -p "$LOG_DIR" && chmod 700 "$LOG_DIR" && chown root:root "$LOG_DIR"
    mkdir -p "$STATUS_DIR" && chmod 755 "$STATUS_DIR" && chown root:root "$STATUS_DIR"
    ECCUBE_ROOT=$(awk '/^root_path:/{print $2}' "$daemon_f")
    _read_interval_from_timer
    install_systemd_files
    systemctl restart eccube-fim-check.timer
}

# ---------------------------------------------------------------------------
# Post-install verification offer
# ---------------------------------------------------------------------------
# known: 43 lines — sequential prompt flow; splitting would require passing $run_validate as state
post_install_checks() {
    echo
    local fim_cmd="$SBIN_DIR/eccube-fim"

    if [ "$NONINTERACTIVE" -eq 1 ]; then
        info "Next: $fim_cmd config validate"
        if [ "${EMAIL_ENABLED:-true}" = "true" ]; then
            info "Next: $fim_cmd test mail"
        fi
        info "Finished."
        return
    fi

    # empty Enter → variable is "", which is != "n", so default is Y
    local run_validate

    if [ ! -x "$fim_cmd" ]; then
        warn "$fim_cmd not found or not executable — run config validate/test mail manually after fixing install"
        info "Finished."
        return
    fi

    read -rp "Run '$fim_cmd config validate' now? [Y/n]: " run_validate </dev/tty
    if [ "${run_validate,,}" != "n" ]; then
        echo
        if "$fim_cmd" config validate </dev/null; then
            if [ "${EMAIL_ENABLED:-true}" = "true" ]; then
                local run_testmail
                read -rp "Send test email via '$fim_cmd test mail' now? [Y/n]: " run_testmail </dev/tty
                if [ "${run_testmail,,}" != "n" ]; then
                    echo
                    "$fim_cmd" test mail </dev/null || warn "test mail failed — check notify.yaml and SMTP credentials"
                fi
            fi
        else
            warn "validate failed — fix config before running test mail"
        fi
    fi

    echo
    info "Finished."
    return 0
}

