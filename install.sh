#!/bin/bash
# install.sh - EC-CUBE FIM install script
# Run as root on a systemd Linux host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SBIN_DIR=/usr/local/sbin
LIB_DIR=/usr/local/lib/eccube-fim
CONFIG_DIR=/etc/eccube-fim
LOG_DIR=/var/log/eccube-fim
RUN_DIR=/var/run/eccube-fim
ECCUBE_ROOT=${ECCUBE_ROOT:-/var/www/html}

info()  { echo -e "\033[32m[INFO]\033[0m  $*"; }
warn()  { echo -e "\033[33m[WARN]\033[0m  $*"; }
error() { echo -e "\033[31m[ERROR]\033[0m $*" >&2; }

detect_os() {
    [ -f /etc/os-release ] || { echo "unknown"; return; }
    # shellcheck source=/dev/null
    . /etc/os-release
    echo "${ID:-unknown}"
}

require_root() {
    [ "$(id -u)" -eq 0 ] || { error "Must be run as root"; exit 1; }
}

configure_os() {
    OS_ID=$(detect_os)
    case "$OS_ID" in
        ol|rhel|centos|rocky|almalinux|fedora)
            PKG_MGR="dnf"; PYYAML_PKG="python3-pyyaml"; WEB_USER="apache" ;;
        ubuntu|debian|linuxmint|pop)
            PKG_MGR="apt-get"; PYYAML_PKG="python3-yaml"; WEB_USER="www-data" ;;
        opensuse*|sles|sled)
            PKG_MGR="zypper"; PYYAML_PKG="python3-PyYAML"; WEB_USER="wwwrun" ;;
        arch|manjaro|endeavouros)
            PKG_MGR="pacman"; PYYAML_PKG="python-yaml"; WEB_USER="http" ;;
        alpine)
            error "Alpine Linux is not supported (OpenRC — systemd required)"; exit 1 ;;
        *)
            error "Unsupported OS: $OS_ID"; exit 1 ;;
    esac
}

install_packages() {
    info "Installing packages with $PKG_MGR"
    case "$PKG_MGR" in
        dnf) dnf install -y python3 "$PYYAML_PKG" git ;;
        apt-get)
            apt-get update -qq
            apt-get install -y --no-install-recommends python3 "$PYYAML_PKG" git
            ;;
        zypper) zypper install -y python3 "$PYYAML_PKG" git ;;
        pacman) pacman -Sy --noconfirm python "$PYYAML_PKG" git ;;
    esac
}

create_directories() {
    info "Creating directories"
    for dir in "$CONFIG_DIR" "$LOG_DIR" "$RUN_DIR"; do
        mkdir -p "$dir"
        chmod 700 "$dir"
        chown root:root "$dir"
    done
    # LIB_DIR is world-readable (755) so the Python interpreter can import from it.
    # install_library() creates it and sets permissions in one step.
}

setup_tmpfiles() {
    # /run is tmpfs on systemd distros; recreate runtime dir after reboot.
    cat > /etc/tmpfiles.d/eccube-fim.conf <<EOF
d $RUN_DIR 0700 root root -
EOF
    systemd-tmpfiles --create /etc/tmpfiles.d/eccube-fim.conf
    info "Configured tmpfiles.d for $RUN_DIR"
}

install_library() {
    info "Installing Python library"
    rm -rf "$LIB_DIR/fim"
    cp -R "$SCRIPT_DIR/fim" "$LIB_DIR/fim"
    find "$LIB_DIR" -type d -exec chmod 755 {} \;
    find "$LIB_DIR" -type f -exec chmod 644 {} \;
    chown -R root:root "$LIB_DIR"
}

install_cli() {
    info "Installing unified CLI"
    install -m 755 -o root -g root "$SCRIPT_DIR/bin/eccube-fim" "$SBIN_DIR/eccube-fim"
}

install_config_samples() {
    for cfg_file in daemon.yaml targets.yaml notify.yaml; do
        if [ -f "$CONFIG_DIR/$cfg_file" ]; then
            info "$CONFIG_DIR/$cfg_file already exists, skipping"
            continue
        fi
        install -m 600 -o root -g root \
            "$SCRIPT_DIR/config/${cfg_file%.yaml}.yaml.sample" \
            "$CONFIG_DIR/$cfg_file"
        warn "Created $CONFIG_DIR/$cfg_file - edit before use"
    done
}

secure_git_dir() {
    if [ ! -d "$ECCUBE_ROOT/.git" ]; then
        warn "$ECCUBE_ROOT/.git not found"
        return
    fi
    chown -R root:root "$ECCUBE_ROOT/.git"
    chmod -R go-rwx "$ECCUBE_ROOT/.git"
    info ".git permissions set to root:root go-rwx"
    if ! id "$WEB_USER" >/dev/null 2>&1; then
        warn "Web user '$WEB_USER' not found - verify .git permissions manually"
        return
    fi
    # su -s avoids a sudo dependency on minimal production installs.
    if su -s /bin/sh "$WEB_USER" -c "ls $ECCUBE_ROOT/.git" >/dev/null 2>&1; then
        warn "$WEB_USER can access .git - check permissions"
    else
        info "$WEB_USER .git access denied"
    fi
}

warn_uncommitted_changes() {
    if ! git -C "$ECCUBE_ROOT" status --porcelain 2>/dev/null | grep -qE '^[MD]'; then
        return
    fi
    warn "Uncommitted changes detected in $ECCUBE_ROOT"
    git -C "$ECCUBE_ROOT" status --short
}

install_systemd_units() {
    info "Installing systemd units"
    install -m 644 -o root -g root "$SCRIPT_DIR/eccube-fim-check.service" /etc/systemd/system/
    install -m 644 -o root -g root "$SCRIPT_DIR/eccube-fim-check.timer" /etc/systemd/system/
    systemctl daemon-reload
    systemctl enable --now eccube-fim-check.timer
}

install_logrotate() {
    info "Installing logrotate config"
    install -m 644 -o root -g root "$SCRIPT_DIR/eccube-fim.logrotate" /etc/logrotate.d/eccube-fim
}

main() {
    require_root
    configure_os
    info "EC-CUBE FIM install (OS: $OS_ID, web user: $WEB_USER)"
    install_packages
    create_directories
    setup_tmpfiles
    install_library
    install_cli
    install_config_samples
    secure_git_dir
    warn_uncommitted_changes
    install_systemd_units
    install_logrotate
    info "Install complete"
    info "Edit $CONFIG_DIR/daemon.yaml, targets.yaml, and notify.yaml"
    info "Then run: eccube-fim test --validate"
}

main "$@"
