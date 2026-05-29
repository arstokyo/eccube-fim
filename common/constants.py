# Install paths — must match install.sh constants exactly
DEFAULT_CONFIG_DIR    = "/etc/eccube-fim"
DEFAULT_SMTP_PORT     = 587
INSTALL_SBIN_DIR      = "/usr/local/sbin"
# CLI binary paths — shared so fim/ and malware/ need not duplicate each other's
# path across the import boundary (fim/ must not import malware/ and vice versa)
INSTALL_FIM_BIN       = f"{INSTALL_SBIN_DIR}/eccube-fim"
INSTALL_MALWARE_BIN   = f"{INSTALL_SBIN_DIR}/eccube-malware"
INSTALL_LIB_DIR       = "/usr/local/lib/eccube-fim"
INSTALL_SYSTEMD_DIR   = "/etc/systemd/system"
INSTALL_LOGROTATE_DIR = "/etc/logrotate.d"
# /run is tmpfs on systemd; stamp disappears after reboot — forces a fresh check after restart
VERSION_CHECK_STAMP   = "/run/eccube-fim/version_check"
INSTALL_STATUS_DIR    = "/var/lib/eccube-fim"
INSTALL_STATUS_FILE   = "/var/lib/eccube-fim/status.json"
# Presence of this file means eccube-malware is installed; used by FIM uninstall guard
INSTALL_MALWARE_MARKER = "/var/lib/eccube-fim/malware-installed"
FETCH_TIMEOUT          = 5   # seconds; used for all outbound HTTP requests to GitHub API
