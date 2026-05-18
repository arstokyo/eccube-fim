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
- Check interval in minutes (default `5`)
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

## Development setup

After cloning, run once to install the pre-commit hook:

```bash
./scripts/install-hooks.sh
```

The hook auto-rebuilds `install.sh` whenever `lib/installer/*.sh` or `build.sh`
is staged, so you never need to run `./build.sh` manually.

To edit the installer, change the relevant file under `lib/installer/` and commit — the hook handles the rest.
