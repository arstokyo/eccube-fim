# eccube-fim

File integrity monitoring for EC-CUBE. Detects twig template tampering via git diff and sends alerts by email (and optionally Slack) within minutes.

Runs as a systemd timer on Oracle Linux 9 / RHEL / Ubuntu 24.04.

---

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/arstokyo/eccube-fim/main/install.sh | sudo bash
```

The installer will ask for:
- EC-CUBE root path (default `/var/www/html`)
- Check interval in minutes (default `5`)
- SMTP host, port, user, and password
- Alert recipients (comma-separated email addresses)
- Slack webhook URLs (optional)

After install, verify everything works:

```bash
eccube-fim validate
eccube-fim test-mail
```

---

## Requirements

- Root access (installer runs as root)
- systemd
- EC-CUBE document root under git version control
- SMTP account for email alerts

Supported OS: Oracle Linux 9, RHEL 9, Ubuntu 24.04, openSUSE Leap 15, Arch Linux

---

## After install

| Task | Command |
|---|---|
| Check monitoring status | `systemctl status eccube-fim-check.timer` |
| View recent alerts | `journalctl -u eccube-fim-check -n 50` |
| Run a manual check now | `eccube-fim check` |
| Approve a legitimate change | `eccube-fim approve <file> --message "reason"` |
| Update to latest version | `sudo eccube-fim upgrade` |
| Change SMTP or root path | `curl -fsSL https://raw.githubusercontent.com/arstokyo/eccube-fim/main/install.sh \| sudo bash -s -- --reconfigure` |

Monitored files are listed in `/etc/eccube-fim/targets.yaml`. Edit that file to add or remove files — no reinstall needed.
