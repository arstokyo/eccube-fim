# known: 163 lines — flat command registry; no natural split boundary
import argparse
import sys
from typing import Optional

from fim.config import Config


def cmd_check(args: argparse.Namespace, cfg: Config) -> int:
    from fim.check import run
    from fim.config import VERSION_CHECK_STAMP
    from fim.version import warn_if_update
    # rate-limited to once per 24h — check is on a 5-min systemd loop
    warn_if_update(args.config_dir, VERSION_CHECK_STAMP)
    return run(cfg, dry_run=args.dry_run, verbose=args.verbose)


def cmd_validate(args: argparse.Namespace, cfg: Config) -> int:
    from fim.validate import validate_config
    from fim.version import warn_if_update
    warn_if_update(args.config_dir)
    return 0 if validate_config(cfg) else 1


def cmd_test_mail(args: argparse.Namespace, cfg: Config) -> int:
    from fim.validate import send_test_mail
    from fim.version import warn_if_update
    warn_if_update(args.config_dir)
    return send_test_mail(cfg)


def cmd_test_slack(args: argparse.Namespace, cfg: Config) -> int:
    from fim.validate import send_test_slack
    from fim.version import warn_if_update
    warn_if_update(args.config_dir)
    return send_test_slack(cfg)


def cmd_approve(args: argparse.Namespace, cfg: Config) -> int:
    from fim.ops import approve_change
    from fim.version import warn_if_update
    warn_if_update(args.config_dir)
    return 0 if approve_change(cfg, args.file_path, message=args.message) else 1


def cmd_upgrade(args: argparse.Namespace, cfg: Optional[Config]) -> int:
    from fim.upgrade import upgrade
    return upgrade(
        yes=args.yes,
        force=args.force,
        migrate_only=args.migrate_only,
        config_dir=args.config_dir,
    )


def cmd_migrate(args: argparse.Namespace, cfg: Optional[Config]) -> int:
    from fim.migration import run_migrations
    try:
        count = run_migrations(args.config_dir)
    except RuntimeError as e:
        print(f"Migration error: {e}", file=sys.stderr)
        return 1
    print(f"Migrations applied: {count}")
    return 0


def cmd_uninstall(args: argparse.Namespace, cfg: Optional[Config]) -> int:
    from fim.lifecycle import uninstall
    return uninstall(keep_config=args.keep_config, yes=args.yes)


def cmd_config_show(args: argparse.Namespace, cfg: Config) -> int:
    from fim.editor import show_config
    show_config(cfg, args.config_dir)
    return 0


def cmd_config_edit(args: argparse.Namespace, cfg: Optional[Config]) -> int:
    from fim.editor import edit_config_file
    return edit_config_file(args.config_dir, args.file)


def cmd_config_timer(args: argparse.Namespace, cfg: Optional[Config]) -> int:
    from fim.timer_ops import show_timer, set_timer_interval, parse_interval_arg, format_interval
    if args.interval is None:
        return show_timer()
    try:
        minutes = parse_interval_arg(args.interval)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    try:
        set_timer_interval(minutes)
    except (OSError, RuntimeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    print(f"Timer interval set to {format_interval(minutes)} — timer restarted.")
    return 0


def cmd_config_setup_notify(args: argparse.Namespace, cfg: Optional[Config]) -> int:
    from fim.notify_setup import setup_notify_interactive
    return setup_notify_interactive(args.config_dir)


def cmd_target_list(args: argparse.Namespace, cfg: Optional[Config]) -> int:
    from fim.target_ops import list_targets
    return list_targets(args.config_dir)


def cmd_target_add(args: argparse.Namespace, cfg: Optional[Config]) -> int:
    from fim.target_ops import add_target
    return add_target(args.config_dir, args.file_path)


def cmd_target_remove(args: argparse.Namespace, cfg: Optional[Config]) -> int:
    from fim.target_ops import remove_target
    return remove_target(args.config_dir, args.file_path)


def cmd_template_list(args: argparse.Namespace, cfg: Optional[Config]) -> int:
    from fim.template_ops import list_templates
    return list_templates(args.config_dir)


def cmd_template_show(args: argparse.Namespace, cfg: Optional[Config]) -> int:
    from fim.template_ops import show_template
    return show_template(args.config_dir, args.name)


def cmd_template_edit(args: argparse.Namespace, cfg: Optional[Config]) -> int:
    from fim.template_ops import edit_template
    return edit_template(args.config_dir, args.name)


def cmd_template_reset(args: argparse.Namespace, cfg: Optional[Config]) -> int:
    from fim.template_ops import reset_template
    return reset_template(args.config_dir, args.name)


def cmd_template_preview(args: argparse.Namespace, cfg: Optional[Config]) -> int:
    from fim.template_ops import preview_template
    return preview_template(args.config_dir)


def cmd_status(args: argparse.Namespace, cfg: Config) -> int:
    from fim.observe import status
    return status(cfg)


def cmd_db_list(args: argparse.Namespace, cfg: Config) -> int:
    from fim.observe import db_list
    return db_list(cfg)


def cmd_db_clear(args: argparse.Namespace, cfg: Config) -> int:
    from fim.observe import db_clear
    return db_clear(cfg, file_path=args.file, yes=args.yes)


def cmd_log(args: argparse.Namespace, cfg: Optional[Config]) -> int:
    from fim.observe import log_tail
    return log_tail(lines=args.lines, level=args.level)
