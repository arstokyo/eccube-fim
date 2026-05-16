# ---------------------------------------------------------------------------
# Package + directory setup
# ---------------------------------------------------------------------------
_check_sshd_health() {
    # sshd -t validates both config and OpenSSL ABI linkage
    if ! sshd -t >/dev/null 2>&1; then
        error "sshd validation failed after package install — do NOT disconnect this session"
        error "Recovery: dnf update openssh openssh-server -y && systemctl restart sshd"
        error "Verify  : sshd -t && ss -tlnp | grep :22"
        exit 1
    fi
}

install_packages() {
    info "Installing packages with $PKG_MGR"
    case "$PKG_MGR" in
        dnf)
            warn "Keep a second SSH session open — package operations may update OpenSSL"
            dnf install -y --setopt=install_weak_deps=False python3 "$PYYAML_PKG" git
            _check_sshd_health
            ;;
        apt-get) apt-get update -qq
                 apt-get install -y --no-install-recommends python3 "$PYYAML_PKG" git ;;
        zypper)  zypper install -y python3 "$PYYAML_PKG" git ;;
        pacman)  pacman -Sy --noconfirm python "$PYYAML_PKG" git ;;
    esac
}

create_directories() {
    info "Creating directories"
    for dir in "$CONFIG_DIR" "$LOG_DIR" "$RUN_DIR"; do
        mkdir -p "$dir"
        chmod 700 "$dir"
        chown root:root "$dir"
    done
    mkdir -p "$LIB_DIR"
    chmod 755 "$LIB_DIR"
    chown root:root "$LIB_DIR"
}

setup_tmpfiles() {
    # /run is tmpfs on systemd distros; recreate runtime dir after reboot
    cat > /etc/tmpfiles.d/eccube-fim.conf <<EOF
d $RUN_DIR 0700 root root -
EOF
    systemd-tmpfiles --create /etc/tmpfiles.d/eccube-fim.conf
    info "Configured tmpfiles.d for $RUN_DIR"
}

