# Shared Architecture — `common/` Package

This document describes the `common/` package shared between
`eccube-fim` (file integrity monitor) and `eccube-malware` (ClamAV scanner).

---

## Why `common/` exists

Both tools send email and Slack alerts, run database migrations, and share
the same config directory (`/etc/eccube-fim/`). Before `common/` was extracted,
all reusable code lived inside `fim/`, which forced `malware/` to either
duplicate it or import from `fim/` — breaking malware-only installations.

`common/` holds exactly the code that neither tool exclusively owns: code with
no single responsible tool.

---

## Module map

| Module | Contents | Used by |
|--------|---------|---------|
| `common/constants.py` | `DEFAULT_CONFIG_DIR`, `INSTALL_*` path constants, `FETCH_TIMEOUT`, `INSTALL_MALWARE_MARKER` | both tools + both installers |
| `common/exceptions.py` | `FimConfigError` | both config loaders |
| `common/utils.py` | `JST` timezone constant | anywhere a timestamp is formatted |
| `common/log.py` | `setup_logging(verbose)` | both CLI entry points |
| `common/version.py` | `__version__`, `REPO_SLUG`, `warn_if_update()`, `read_installed_version()`, `parse_python_requires()`, `python_meets()` | both CLIs at startup |
| `common/config.py` | `load_yaml(path)` — strict YAML loader, raises `FimConfigError` on missing/invalid | both `config.py` loaders |
| `common/db.py` | `@db_transaction` decorator | both `db.py` modules |
| `common/migration.py` | `MigrationRunner(db_path, migrations_dir, config_dir)` | both migration wrappers |
| `common/notify_config.py` | `NotifyEmail`, `NotifySlack` dataclasses; `print_secrets_status()`, `parse_notify_channels()`, `validate_notify_channels()` | embedded in `Config` and `MalwareConfig`; both `config.py` loaders and `validate.py` |
| `common/notify/__init__.py` | `NotifyConfigLike` Protocol, `_REGISTRY`, `build_channels()`, `send_safe()` | both `dispatch_*` functions |
| `common/notify/base.py` | `Channel` Protocol, `RenderedNotification` dataclass | all notify modules |
| `common/notify/email.py` | `EmailChannel` | via `build_channels()` |
| `common/notify/slack.py` | `SlackChannel` | via `build_channels()` |
| `common/notify_setup.py` | `setup_notify_interactive()` | both `config setup-notify` commands |
| `common/editor.py` | `file_hash()`, `open_in_editor()` | both `editor.py` modules |
| `common/template_ops.py` | `load_template()`, `resolve_template()`, `validate_template_vars()`, `unknown_template()` | both `template.py` and `template_ops.py` modules |
| `common/upgrade.py` | `run_upgrade()` (full orchestration), `fetch_release_info()`, `check_python_requires()`, `download_tarball()`, `find_extracted_root()`, `run_companion_migrations()`, `migrate_only()`, `confirm_co_upgrade()`, `write_version_stamp()` | both `upgrade.py` modules |
| `common/lifecycle.py` | `require_root()`, `stop_and_disable_units()`, `remove_unit_files()`, `remove_lib_subdir()`, `remove_common_if_no_companion()`, `fim_installed()`, `remove_common_if_fim_absent()` | both `lifecycle.py` modules |
| `common/status.py` | `atomic_write_json()` — atomic file write with chmod 644 | both `status_writer.py` modules |

---

## The `NotifyConfigLike` Protocol — duck-typed channel building

`build_channels()` accepts both `Config` (FIM) and `MalwareConfig` (malware)
without importing either. It uses a structural Protocol:

```python
# common/notify/__init__.py
class NotifyConfigLike(Protocol):
    email: NotifyEmail
    slack: NotifySlack

# Registry: (predicate, factory). To add a channel: append one tuple here.
_REGISTRY = [
    (lambda cfg: cfg.email.enabled, lambda cfg: EmailChannel(cfg.email)),
    (lambda cfg: cfg.slack.enabled, lambda cfg: SlackChannel(cfg.slack)),
]

def build_channels(cfg: NotifyConfigLike) -> list[Channel]:
    return [factory(cfg) for enabled, factory in _REGISTRY if enabled(cfg)]
```

Any object with `.email: NotifyEmail` and `.slack: NotifySlack` satisfies
`NotifyConfigLike`. No explicit inheritance is needed. Adding a third channel
type means appending one tuple to `_REGISTRY` — `build_channels()` needs no
other change.

---

## Migration isolation

Both tools share `MigrationRunner` but run completely separate migrations:

```
FIM:
  MigrationRunner(
      db_path        = "/etc/eccube-fim/state.db",
      migrations_dir = "fim/migrations/",
      config_dir     = "/etc/eccube-fim",
  )

Malware:
  MigrationRunner(
      db_path        = "/etc/eccube-fim/malware_state.db",
      migrations_dir = "malware/migrations/",
      config_dir     = "/etc/eccube-fim",
  )
```

Each tool's migrations track their own `schema_migrations` table inside their
own SQLite file. Installing or uninstalling one tool never touches the other
tool's database.

---

## Config file isolation

```
/etc/eccube-fim/
├── daemon.yaml          FIM only   — root_path, heartbeat, state_db
├── targets.yaml         FIM only   — target_files, suppress_window_hours
├── notify.yaml          SHARED     — email and Slack settings for both tools
├── malware.yaml         Malware    — scan_targets, exclude_dirs, log_dir, state_db
├── state.db             FIM only   — git-diff dedup records
├── malware_state.db     Malware    — ClamAV detection dedup records
├── smtp.password        SHARED     — SMTP password (read at send time)
└── slack-N.webhook      SHARED     — Slack webhook URL files (read at send time)
```

`notify.yaml`, `smtp.password`, and `slack-N.webhook` are configured once and
used by both tools. A single `eccube-fim config setup-notify` or
`eccube-malware config setup-notify` call writes to the same `notify.yaml`.

On a malware-only installation (no FIM), the installer's `wizard_notify` writes
`notify.yaml` during `install-malware.sh`. On a co-install, FIM's `wizard()`
writes it and the malware installer skips (file already exists).

---

## Install / uninstall isolation

```
/usr/local/lib/eccube-fim/
├── common/    shared — never removed while either tool is installed
├── fim/       FIM only
└── malware/   malware only
```

| Scenario | `common/` | `fim/` | `malware/` |
|----------|-----------|--------|-----------|
| FIM install | installed | installed | — |
| Malware install | installed | — | installed |
| Both installed | installed (same files) | installed | installed |
| FIM uninstall | kept if malware marker present; else removed | removed | unchanged |
| Malware uninstall | kept if FIM binary present; else removed | unchanged | removed |

Each uninstaller removes `common/` only when its companion tool is absent:

- The FIM uninstaller (`fim/lifecycle.py`) calls `remove_common_if_no_companion()`,
  which checks for the `/var/lib/eccube-fim/malware-installed` marker
  (`INSTALL_MALWARE_MARKER`) before removing `common/`.
- The malware uninstaller (`malware/lifecycle.py`) calls
  `remove_common_if_fim_absent()`, which checks for the installed
  `eccube-fim` binary (`INSTALL_FIM_BIN`) before removing `common/`.

Whichever tool is uninstalled last takes `common/` with it.

---

## `fim/` re-export pattern

Some `fim/` modules that originally defined symbols now re-export them from
`common/` to preserve backward compatibility for existing import paths:

```python
# fim/exceptions.py
from common.exceptions import FimConfigError  # noqa: F401

# fim/log.py
from common.log import setup_logging  # noqa: F401
```

External code and tests that import from `fim.*` are unaffected.

---

## Adding a third tool

To add a new tool (e.g. `eccube-waf/`) that shares the notification stack:

1. Create `waf/config.py` with a `WafConfig` dataclass that includes
   `email: NotifyEmail` and `slack: NotifySlack` fields.
2. Load config via `common.config.load_yaml` reading `waf.yaml` + `notify.yaml`.
3. Call `build_channels(cfg)` — `WafConfig` satisfies `NotifyConfigLike` automatically.
4. Create `waf/migrations/` and call `MigrationRunner` with `waf_state.db` as `db_path`.
5. Add a `waf/status_writer.py` that calls `common.status.atomic_write_json()`.
6. Install only `common/` + `waf/` — never depend on `fim/` or `malware/`.

No changes to `common/` are needed for a new tool to achieve structural parity.

---

## What is intentionally NOT shared

| Concern | Reason not shared |
|---------|------------------|
| `Detection` / `MalwareDetection` dataclasses | Different fields (git diff vs. virus name) |
| `dispatch_notifications()` / `dispatch_malware_notifications()` | Different input types and template variables |
| `render_subject/email/slack()` functions | Different template variables per tool |
| `Db` / `MalwareDb` classes | Different DB schemas |
| `Config` / `MalwareConfig` dataclasses | Different tool-specific keys |
| `timer_ops` | FIM uses minute intervals (`*/N`); malware uses time-of-day (`HH:MM`) |
| `observe` / `status_writer` dashboards | Different fields (heartbeat vs. ClamAV version + scan status) |
| Log directories | FIM: `/var/log/eccube-fim`; malware: `/var/log/clamav` |
| `clamav_version.py` | ClamAV package version detection and 24h cache — malware-specific |
| `clamav_updater.py` | ClamAV package upgrade via dnf/apt-get — malware-specific |
