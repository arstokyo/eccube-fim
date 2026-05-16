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

