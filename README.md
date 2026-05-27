# eccube-fim

File integrity monitoring for EC-CUBE. Detects twig template tampering via git diff
and sends alerts by email (and optionally Slack) within minutes.

Runs as a systemd timer on Oracle Linux 9 / RHEL / Ubuntu 24.04.

---

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/arstokyo/eccube-fim/main/install.sh | sudo bash
```

The installer will ask for:
- EC-CUBE root path (default `/var/www/html`)
- Check interval in minutes (default `15`)
- SMTP host, port, user, and password
- Alert recipients (comma-separated email addresses)
- Slack webhook URLs (optional)

After install, verify everything works:

```bash
eccube-fim config validate
eccube-fim test mail
```

---

## Requirements

- Root access (installer runs as root)
- systemd
- EC-CUBE document root under git version control
- SMTP account for email alerts

Supported OS: Oracle Linux 9, RHEL 9, Ubuntu 24.04, openSUSE Leap 15, Arch Linux

---

## Malware Scanner

ClamAV-based scanner for the EC-CUBE web root. Runs daily, sends email and
Slack alerts on detection, suppresses duplicate alerts within a configurable
window.

### Install

```bash
curl -fsSL https://raw.githubusercontent.com/arstokyo/eccube-fim/main/install-malware.sh | sudo bash
```

The installer will:
- Install ClamAV (`clamscan`, `freshclam`) for your OS
- Copy `eccube-malware` to `/usr/local/sbin/`
- Create `/etc/eccube-fim/malware.yaml` (edit scan paths before use)
- Enable `clamav-scan.timer` (daily 03:00) and `clamav-freshclam.timer` (every 3h)
- Run an initial `freshclam` signature update

After install, edit the scan targets and verify:

```bash
vi /etc/eccube-fim/malware.yaml   # set scan_targets
eccube-malware config validate
eccube-malware test mail
eccube-malware check --dry-run
```

### Requirements

- Root access
- systemd
- Network access for ClamAV signature updates (`freshclam`)
- SMTP account for email alerts (shared with eccube-fim if both are installed)

Supported OS: Oracle Linux 9, RHEL 9, Ubuntu 24.04

### Notification config

If eccube-fim is already installed, `eccube-malware` reuses the same
`/etc/eccube-fim/notify.yaml`. No additional email/Slack setup needed.

If installing malware scanner standalone, run the setup wizard:

```bash
eccube-malware config setup-notify
```

---

## Plugin (EC-CUBE Admin Dashboard)

The plugin adds a read-only FIM status dashboard to the EC-CUBE admin panel
(`/admin/fim`). It requires the eccube-fim daemon to be installed first.

**Step 1 — Copy plugin files (run as root):**

```bash
curl -fsSL https://raw.githubusercontent.com/arstokyo/eccube-fim/main/plugin/install-plugin.sh | sudo bash
```

The script reads `root_path` from `/etc/eccube-fim/daemon.yaml` and copies the
plugin into `<eccube-root>/app/Plugin/EccubeFim/`.

**Step 2 — Activate via EC-CUBE console:**

```bash
cd /var/www/html   # your EC-CUBE root
php bin/console eccube:plugin:install --code=EccubeFim
php bin/console eccube:plugin:enable  --code=EccubeFim
php bin/console cache:clear --env=prod --no-warmup
```

The script prints these exact commands with the correct path after it finishes.

**Dashboard:** `https://<your-site>/admin/fim`

---

## CLI reference

All commands require root (`sudo`) except where noted.

### Daily operations

| Command | Description |
|---|---|
| `eccube-fim check` | Run an integrity check immediately (systemd runs this automatically) |
| `eccube-fim approve <file> -m "reason"` | Mark a detected change as intentional; clears the alert |
| `eccube-fim status` | Dashboard: service state, last heartbeat, DB record count, last log line |
| `eccube-fim log` | Tail the check log (last 20 lines); `--lines N` or `--level ERROR` to filter |

### Configuration

| Command | Description |
|---|---|
| `eccube-fim config show` | Print the merged effective config from all three YAML files |
| `eccube-fim config validate` | Validate all config files and print a status report |
| `eccube-fim config edit [daemon\|targets\|notify]` | Open a config file in `$EDITOR`; validates on save |
| `eccube-fim config timer [INTERVAL]` | Show or change the check interval (e.g. `5`, `30`, `1h`) |
| `eccube-fim config setup-notify` | Interactive wizard to enable or reconfigure email/Slack |

### Monitored files

Managed via `config target`; persisted to `/etc/eccube-fim/targets.yaml`.

| Command | Description |
|---|---|
| `eccube-fim config target list` | List all monitored file paths |
| `eccube-fim config target add <path>` | Add a file (path relative to EC-CUBE root) |
| `eccube-fim config target remove <path>` | Remove a file from monitoring |

### Notification templates

Override built-in email/Slack message templates without editing config YAML.

| Command | Description |
|---|---|
| `eccube-fim config template list` | Show all templates and whether a user override is active |
| `eccube-fim config template show <name>` | Print the active template (`subject`, `email`, or `slack`) |
| `eccube-fim config template edit <name>` | Open (or create) an override in `$EDITOR` |
| `eccube-fim config template reset <name>` | Delete override and revert to built-in |
| `eccube-fim config template preview` | Render all templates with sample data |

### Diagnostics

| Command | Description |
|---|---|
| `eccube-fim test mail` | Send a test email via SMTP to verify channel reachability |
| `eccube-fim test slack` | Send a test Slack message via webhook |
| `eccube-fim db list` | Show all deduplication state records (suppressed alerts) |
| `eccube-fim db clear` | Remove dedup records — all, or `--file <path>` for one file |

### Lifecycle

| Command | Description |
|---|---|
| `eccube-fim upgrade` | Download and install the latest release |
| `eccube-fim uninstall` | Stop the service and remove all installed files |

---

## eccube-malware CLI reference

All commands require root (`sudo`).

### Daily operations

| Command | Description |
|---|---|
| `eccube-malware check` | Run a ClamAV scan immediately (systemd runs this automatically at 03:00) |
| `eccube-malware check --dry-run` | Scan and log detections but skip notifications |
| `eccube-malware status` | Dashboard: timer state, last scan log, suppression DB count, ClamAV version |
| `eccube-malware log` | Tail the most recent scan log (last 20 lines); `--lines N` or `--level ERROR` |

### Configuration

| Command | Description |
|---|---|
| `eccube-malware config show` | Print effective config from `malware.yaml` + `notify.yaml` |
| `eccube-malware config validate` | Validate config files and print a status report |
| `eccube-malware config edit [malware\|notify]` | Open a config file in `$EDITOR`; validates on save |
| `eccube-malware config timer [HH:MM]` | Show or change the daily scan time (e.g. `03:00`, `02:30`) |
| `eccube-malware config setup-notify` | Interactive wizard to enable or reconfigure email/Slack |

### Scan targets

Managed via `config target`; persisted to `/etc/eccube-fim/malware.yaml`.

| Command | Description |
|---|---|
| `eccube-malware config target list` | List all scan target paths |
| `eccube-malware config target add <path>` | Add a directory path to `scan_targets` |
| `eccube-malware config target remove <path>` | Remove a directory path from `scan_targets` |

### Notification templates

| Command | Description |
|---|---|
| `eccube-malware config template list` | Show all templates and whether a user override is active |
| `eccube-malware config template show <name>` | Print the active template (`subject`, `email`, or `slack`) |
| `eccube-malware config template edit <name>` | Open (or create) an override in `$EDITOR` |
| `eccube-malware config template reset <name>` | Delete override and revert to built-in |
| `eccube-malware config template preview` | Render all templates with sample detection data |

### Diagnostics

| Command | Description |
|---|---|
| `eccube-malware test mail` | Send a test email to verify SMTP reachability |
| `eccube-malware test slack` | Send a test Slack message via webhook |
| `eccube-malware db list` | Show all suppressed detection records |
| `eccube-malware db clear` | Remove suppression records — all, or `--file <path>` for one file |

### Lifecycle

| Command | Description |
|---|---|
| `eccube-malware upgrade` | Download and install the latest release |
| `eccube-malware uninstall` | Stop timers and remove all installed files; `--keep-config` preserves `malware.yaml` and the suppression DB |

---

## Development setup

After cloning, run once to install the pre-commit hook:

```bash
./scripts/install-hooks.sh
```

The hook auto-rebuilds `install.sh` whenever `lib/installer/*.sh` or `build.sh`
is staged, so you never need to run `./build.sh` manually.

To edit the installer, change the relevant file under `lib/installer/` and commit — the hook handles the rest.
