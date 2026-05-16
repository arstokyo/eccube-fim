#!/bin/bash
# install.sh — EC-CUBE FIM install / update / reconfigure
# Run as root on a systemd Linux host.
set -euo pipefail

SBIN_DIR=/usr/local/sbin
LIB_DIR=/usr/local/lib/eccube-fim
CONFIG_DIR=/etc/eccube-fim
LOG_DIR=/var/log/eccube-fim
RUN_DIR=/run/eccube-fim

REPO_SLUG="arstokyo/eccube-fim"
REPO="https://github.com/${REPO_SLUG}"
RELEASES_API="https://api.github.com/repos/${REPO_SLUG}/releases/latest"

NONINTERACTIVE=0
RECONFIGURE=0
UPDATE=0
VERSION=""          # set by _fetch_release_info()
PYTHON_REQUIRES=""  # set by _fetch_release_info()
SRC_DIR=""

