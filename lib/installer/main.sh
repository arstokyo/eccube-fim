# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
# known: 35 lines — orchestration function; length reflects install steps, not complexity
main() {
    parse_args "$@"
    require_root
    configure_os

    if [ "$UPDATE" -eq 1 ]; then
        fetch_source
        info "EC-CUBE FIM installer (version: ${VERSION}, OS: ${OS_ID})"
        install_packages
        update_mode
        install_post_merge_hook
        info "Update complete"
        post_install_checks
        return
    fi

    fetch_source
    info "EC-CUBE FIM installer (version: ${VERSION}, OS: ${OS_ID})"
    install_packages
    create_directories
    setup_tmpfiles
    install_library
    install_cli
    install_logrotate
    wizard
    secure_git_dir
    install_post_merge_hook
    _warn_root_ssh
    warn_uncommitted_changes
    install_systemd_files
    activate_systemd_units
    info "Install complete"
    post_install_checks
    return 0
}

main "$@"
exit $?
