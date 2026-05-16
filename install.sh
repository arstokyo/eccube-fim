#!/bin/bash
# install.sh — EC-CUBE FIM install / update / reconfigure
# Run as root on a systemd Linux host.
set -euo pipefail

SBIN_DIR=/usr/local/sbin
LIB_DIR=/usr/local/lib/eccube-fim
CONFIG_DIR=/etc/eccube-fim
LOG_DIR=/var/log/eccube-fim
RUN_DIR=/var/run/eccube-fim

REPO="https://github.com/arstokyo/eccube-fim"
RELEASES_API="https://api.github.com/repos/arstokyo/eccube-fim/releases/latest"

NONINTERACTIVE=0
RECONFIGURE=0
UPDATE=0
VERSION=""   # set by fetch_source() after resolving latest release
SRC_DIR=""

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
info()  { echo -e "\033[32m[INFO]\033[0m  $*"; }
warn()  { echo -e "\033[33m[WARN]\033[0m  $*"; }
error() { echo -e "\033[31m[ERROR]\033[0m $*" >&2; }

# ---------------------------------------------------------------------------
# Arg parsing
# ---------------------------------------------------------------------------
parse_args() {
    while [ $# -gt 0 ]; do
        case "$1" in
            --non-interactive) NONINTERACTIVE=1 ;;
            --reconfigure)     RECONFIGURE=1 ;;
            --update)          UPDATE=1 ;;
            *) error "Unknown argument: $1"; exit 1 ;;
        esac
        shift
    done
    if [ "$UPDATE" -eq 1 ] && [ "$RECONFIGURE" -eq 1 ]; then
        error "--update and --reconfigure are mutually exclusive"; exit 1
    fi
}

# ---------------------------------------------------------------------------
# OS detection
# ---------------------------------------------------------------------------
require_root() {
    [ "$(id -u)" -eq 0 ] || { error "Must be run as root"; exit 1; }
}

detect_os() {
    [ -f /etc/os-release ] || { echo "unknown"; return; }
    # shellcheck source=/dev/null
    . /etc/os-release
    echo "${ID:-unknown}"
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

# ---------------------------------------------------------------------------
# Source fetch — latest GitHub Release, fall back to main
# ---------------------------------------------------------------------------
_resolve_version() {
    # Returns the latest release tag, or "main" if no releases exist yet
    local tag
    tag=$(curl -fsSL "$RELEASES_API" 2>/dev/null | grep '"tag_name"' | cut -d'"' -f4)
    echo "${tag:-main}"
}

fetch_source() {
    local script_dir
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || echo "")"
    if [ -d "${script_dir}/fim" ]; then
        SRC_DIR="$script_dir"
        VERSION="local"
        info "Using local source: $SRC_DIR"
        return
    fi
    VERSION=$(_resolve_version)
    info "Downloading eccube-fim (${VERSION})..."
    SRC_DIR="$(mktemp -d)"
    # shellcheck disable=SC2064
    trap "rm -rf '$SRC_DIR'" EXIT
    local url
    if [ "$VERSION" = "main" ]; then
        url="${REPO}/archive/refs/heads/main.tar.gz"
    else
        url="${REPO}/archive/refs/tags/${VERSION}.tar.gz"
    fi
    curl -fsSL "$url" | tar xz --strip-components=1 -C "$SRC_DIR"
    info "Source ready: eccube-fim ${VERSION}"
}

# ---------------------------------------------------------------------------
# Package + directory setup
# ---------------------------------------------------------------------------
install_packages() {
    info "Installing packages with $PKG_MGR"
    case "$PKG_MGR" in
        dnf)     dnf install -y python3 "$PYYAML_PKG" git ;;
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
    # LIB_DIR needs 755 so Python can import from it
}

setup_tmpfiles() {
    # /run is tmpfs on systemd distros; recreate runtime dir after reboot
    cat > /etc/tmpfiles.d/eccube-fim.conf <<EOF
d $RUN_DIR 0700 root root -
EOF
    systemd-tmpfiles --create /etc/tmpfiles.d/eccube-fim.conf
    info "Configured tmpfiles.d for $RUN_DIR"
}

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

install_cli() {
    info "Installing unified CLI"
    install -m 755 -o root -g root "$SRC_DIR/bin/eccube-fim" "$SBIN_DIR/eccube-fim"
}

install_logrotate() {
    info "Installing logrotate config"
    install -m 644 -o root -g root "$SRC_DIR/eccube-fim.logrotate" /etc/logrotate.d/eccube-fim
}

# ---------------------------------------------------------------------------
# Interactive wizard
# ---------------------------------------------------------------------------

# prompt VAR_NAME "Label" "default" [secret]
# Non-interactive: reads from env var $VAR_NAME; aborts if required and unset.
prompt() {
    local var="$1" label="$2" default="$3" secret="${4:-}"
    if [ "$NONINTERACTIVE" -eq 1 ]; then
        local env_val
        env_val="${!var:-}"
        if [ -z "$env_val" ] && [ -z "$default" ]; then
            error "--non-interactive: $var is required but not set"; exit 1
        fi
        printf -v "$var" '%s' "${env_val:-$default}"
        return
    fi
    local display_label="$label"
    [ -n "$default" ] && display_label="$label [$default]"
    local input=""
    if [ -n "$secret" ]; then
        read -rsp "${display_label}: " input; echo
    else
        read -rp "${display_label}: " input
    fi
    printf -v "$var" '%s' "${input:-$default}"
}

prompt_infra() {
    echo
    info "=== Infrastructure ==="
    prompt ECCUBE_ROOT    "EC-CUBE root path"        "/var/www/html"
    prompt CHECK_INTERVAL "Check interval (minutes)" "5"
    [ -d "$ECCUBE_ROOT" ] || warn "$ECCUBE_ROOT not found — create it before starting the service"
    echo "$CHECK_INTERVAL" | grep -qE '^[1-9][0-9]*$' \
        || { error "Interval must be a positive integer"; exit 1; }
}

prompt_email() {
    echo
    info "=== Email alerts ==="
    prompt SMTP_HOST      "SMTP host"                    ""
    prompt SMTP_PORT      "SMTP port"                    "587"
    prompt SMTP_USER      "SMTP user"                    ""
    prompt SMTP_PASSWORD  "SMTP password"                "" secret
    prompt EMAIL_FROM     "From address"                 "$SMTP_USER"
    prompt EMAIL_RCPT_RAW "Recipients (comma-separated)" ""
    [ -n "$EMAIL_RCPT_RAW" ] || { error "At least one recipient is required"; exit 1; }
}

prompt_slack() {
    echo
    info "=== Slack alerts (optional) ==="
    SLACK_ENABLED=false
    SLACK_WEBHOOKS=()
    [ "$NONINTERACTIVE" -eq 1 ] && return
    read -rp "Enable Slack notifications? [y/N]: " yn
    [ "${yn,,}" = "y" ] || return
    SLACK_ENABLED=true
    local i=1
    while true; do
        local wh=""
        read -rp "Slack webhook URL $i (empty to stop): " wh
        [ -z "$wh" ] && break
        local wh_file="$CONFIG_DIR/slack-${i}.webhook"
        printf '%s' "$wh" > "$wh_file"
        chmod 600 "$wh_file"; chown root:root "$wh_file"
        SLACK_WEBHOOKS+=("$wh_file")
        i=$((i + 1))
    done
}

write_daemon_yaml() {
    cat > "$CONFIG_DIR/daemon.yaml" <<EOF
# Generated by eccube-fim install.sh ${VERSION}
root_path: $ECCUBE_ROOT
state_db: $CONFIG_DIR/state.db
heartbeat:
  enabled: true
  file: $RUN_DIR/heartbeat
EOF
    chmod 600 "$CONFIG_DIR/daemon.yaml"; chown root:root "$CONFIG_DIR/daemon.yaml"
    info "Written $CONFIG_DIR/daemon.yaml"
}

write_targets_yaml() {
    local f="$CONFIG_DIR/targets.yaml"
    if [ -f "$f" ] && [ "$RECONFIGURE" -eq 0 ]; then
        info "$f exists — skipping (preserves operator customisations)"
        return
    fi
    cp "$SRC_DIR/config/targets.yaml.sample" "$f"
    chmod 600 "$f"; chown root:root "$f"
    info "Written $f"
}

write_notify_yaml() {
    local rcpt_yaml="" r
    IFS=',' read -ra rcpts <<< "$EMAIL_RCPT_RAW"
    for r in "${rcpts[@]}"; do
        r="${r// /}"
        rcpt_yaml="${rcpt_yaml}    - ${r}"$'\n'
    done
    local slack_files_yaml="" wh_file
    for wh_file in ${SLACK_WEBHOOKS[@]+"${SLACK_WEBHOOKS[@]}"}; do
        slack_files_yaml="${slack_files_yaml}    - ${wh_file}"$'\n'
    done
    cat > "$CONFIG_DIR/notify.yaml" <<EOF
# Generated by eccube-fim install.sh ${VERSION}
email:
  smtp_host: $SMTP_HOST
  smtp_port: $SMTP_PORT
  smtp_user: $SMTP_USER
  smtp_password_file: $CONFIG_DIR/smtp.password
  from: $EMAIL_FROM
  recipients:
${rcpt_yaml}
slack:
  enabled: $SLACK_ENABLED
  webhook_url_files:
${slack_files_yaml}
EOF
    chmod 600 "$CONFIG_DIR/notify.yaml"; chown root:root "$CONFIG_DIR/notify.yaml"
    info "Written $CONFIG_DIR/notify.yaml"
}

write_smtp_password() {
    printf '%s' "$SMTP_PASSWORD" > "$CONFIG_DIR/smtp.password"
    chmod 600 "$CONFIG_DIR/smtp.password"; chown root:root "$CONFIG_DIR/smtp.password"
    info "Written $CONFIG_DIR/smtp.password"
}

_read_interval_from_timer() {
    local calendar
    calendar=$(systemctl cat eccube-fim-check.timer 2>/dev/null | awk -F= '/^OnCalendar=/{print $2}')
    CHECK_INTERVAL="${calendar##*:0/}"
    CHECK_INTERVAL="${CHECK_INTERVAL:-5}"
}

wizard() {
    local daemon_f="$CONFIG_DIR/daemon.yaml"
    local notify_f="$CONFIG_DIR/notify.yaml"
    # Skip wizard whenever configs exist — interactive or not — unless --reconfigure
    if [ -f "$daemon_f" ] && [ -f "$notify_f" ] && [ "$RECONFIGURE" -eq 0 ]; then
        info "Existing config found — skipping wizard (use --reconfigure to change settings)"
        ECCUBE_ROOT=$(awk '/^root_path:/{print $2}' "$daemon_f")
        ECCUBE_ROOT="${ECCUBE_ROOT:-/var/www/html}"
        _read_interval_from_timer
        return
    fi
    prompt_infra
    prompt_email
    prompt_slack
    write_daemon_yaml
    write_targets_yaml
    write_notify_yaml
    write_smtp_password
}

# ---------------------------------------------------------------------------
# Git hardening
# ---------------------------------------------------------------------------
secure_git_dir() {
    if [ ! -d "$ECCUBE_ROOT/.git" ]; then
        warn "$ECCUBE_ROOT/.git not found"
        return
    fi
    chown -R root:root "$ECCUBE_ROOT/.git"
    chmod -R go-rwx "$ECCUBE_ROOT/.git"
    info ".git permissions set to root:root go-rwx"
    if ! id "$WEB_USER" >/dev/null 2>&1; then
        warn "Web user '$WEB_USER' not found — verify .git permissions manually"
        return
    fi
    if su -s /bin/sh "$WEB_USER" -c "ls $ECCUBE_ROOT/.git" >/dev/null 2>&1; then
        warn "$WEB_USER can access .git — check permissions"
    else
        info "$WEB_USER .git access denied"
    fi
}

warn_uncommitted_changes() {
    if ! git -c "safe.directory=$ECCUBE_ROOT" -C "$ECCUBE_ROOT" \
            status --porcelain 2>/dev/null | grep -qE '^[MD]'; then
        return
    fi
    warn "Uncommitted changes detected in $ECCUBE_ROOT"
    git -c "safe.directory=$ECCUBE_ROOT" -C "$ECCUBE_ROOT" status --short
}

# ---------------------------------------------------------------------------
# systemd units — template substitution
# ---------------------------------------------------------------------------
install_systemd_files() {
    info "Installing systemd units (interval: ${CHECK_INTERVAL}m, root: $ECCUBE_ROOT)"
    sed "s|%%ECCUBE_ROOT%%|${ECCUBE_ROOT}|g" \
        "$SRC_DIR/eccube-fim-check.service" \
        > /etc/systemd/system/eccube-fim-check.service
    sed "s|%%INTERVAL%%|${CHECK_INTERVAL}|g" \
        "$SRC_DIR/eccube-fim-check.timer" \
        > /etc/systemd/system/eccube-fim-check.timer
    chmod 644 /etc/systemd/system/eccube-fim-check.service \
              /etc/systemd/system/eccube-fim-check.timer
    systemctl daemon-reload
}

activate_systemd_units() {
    systemctl enable --now eccube-fim-check.timer
}

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
    info "Update complete"
}

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
main() {
    parse_args "$@"
    require_root
    configure_os

    if [ "$UPDATE" -eq 1 ]; then
        fetch_source
        info "EC-CUBE FIM installer (version: ${VERSION}, OS: ${OS_ID})"
        install_packages
        update_mode
        info "Run: eccube-fim test --validate"
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
    warn_uncommitted_changes
    install_systemd_files
    activate_systemd_units
    info "Install complete"
    info "Run: eccube-fim test --validate"
    info "Run: eccube-fim test --send-test-mail"
}

main "$@"
