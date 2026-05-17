import argparse
from typing import Optional

from fim.config import Config


def cmd_check(args: argparse.Namespace, cfg: Config) -> int:
    from fim.check import run
    from fim.version import warn_if_update, VERSION_CHECK_STAMP
    # rate-limited to once per 24h — check is on a 5-min systemd loop
    warn_if_update(VERSION_CHECK_STAMP)
    return run(cfg, dry_run=args.dry_run, verbose=args.verbose)


def cmd_validate(args: argparse.Namespace, cfg: Config) -> int:
    from fim.diagnostics import validate_config
    from fim.version import warn_if_update
    warn_if_update()
    return 0 if validate_config(cfg) else 1


def cmd_test_mail(args: argparse.Namespace, cfg: Config) -> int:
    from fim.diagnostics import send_test_mail
    from fim.version import warn_if_update
    warn_if_update()
    return send_test_mail(cfg)


def cmd_approve(args: argparse.Namespace, cfg: Config) -> int:
    from fim.ops import approve_change
    from fim.version import warn_if_update
    warn_if_update()
    return 0 if approve_change(cfg, args.file_path, message=args.message) else 1


def cmd_upgrade(args: argparse.Namespace, cfg: Optional[Config]) -> int:
    from fim.upgrade import upgrade
    return upgrade(yes=args.yes)


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
