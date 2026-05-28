# Install paths — must match install.sh constants exactly
DEFAULT_CONFIG_DIR    = "/etc/eccube-fim"
DEFAULT_SMTP_PORT     = 587
INSTALL_SBIN_DIR      = "/usr/local/sbin"
INSTALL_LIB_DIR       = "/usr/local/lib/eccube-fim"
INSTALL_SYSTEMD_DIR   = "/etc/systemd/system"
INSTALL_LOGROTATE_DIR = "/etc/logrotate.d"
# /run is tmpfs on systemd; stamp disappears after reboot — forces a fresh check after restart
VERSION_CHECK_STAMP   = "/run/eccube-fim/version_check"
INSTALL_STATUS_DIR    = "/var/lib/eccube-fim"
INSTALL_STATUS_FILE   = "/var/lib/eccube-fim/status.json"
# Presence of this file means eccube-malware is installed; used by FIM uninstall guard
INSTALL_MALWARE_MARKER = "/var/lib/eccube-fim/malware-installed"
