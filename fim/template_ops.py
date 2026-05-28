import socket
from pathlib import Path

from common.template_ops import (
    list_templates_impl,
    show_template_impl,
    edit_template_impl,
    reset_template_impl,
)
from fim._template_data import _REQUIRED_VARS, _SAMPLE_DETECTIONS
from fim.template import (
    BUILTIN_TEMPLATE_DIR, TEMPLATE_NAMES,
    render_subject, render_email_body, render_slack_body,
)


def list_templates(config_dir: str) -> int:
    """Print all template names + whether a user override is active."""
    return list_templates_impl(config_dir, TEMPLATE_NAMES, BUILTIN_TEMPLATE_DIR)


def show_template(config_dir: str, name: str) -> int:
    """Print the active template content (override preferred)."""
    return show_template_impl(config_dir, name, TEMPLATE_NAMES, BUILTIN_TEMPLATE_DIR)


def edit_template(config_dir: str, name: str) -> int:
    """Open (or create) the override template in $EDITOR."""
    return edit_template_impl(
        config_dir, name, TEMPLATE_NAMES, BUILTIN_TEMPLATE_DIR, _REQUIRED_VARS, cycle="check"
    )


def reset_template(config_dir: str, name: str) -> int:
    """Delete the user override so the built-in resumes."""
    return reset_template_impl(config_dir, name, TEMPLATE_NAMES, BUILTIN_TEMPLATE_DIR)


def preview_template(config_dir: str) -> int:
    """Render all templates with sample data and print the result."""
    hostname = socket.gethostname()
    print("=" * 60)
    print("SUBJECT")
    print("=" * 60)
    print(render_subject(hostname, config_dir))
    print()
    print("=" * 60)
    print("EMAIL BODY")
    print("=" * 60)
    print(render_email_body(hostname, _SAMPLE_DETECTIONS, config_dir))
    print()
    print("=" * 60)
    print("SLACK BODY")
    print("=" * 60)
    print(render_slack_body(hostname, _SAMPLE_DETECTIONS, config_dir))
    return 0
