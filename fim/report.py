import sys
from dataclasses import dataclass, field


@dataclass
class _Report:
    """Accumulates verbose diagnostic data during one detection cycle."""
    config_lines: list[str] = field(default_factory=list)
    target_lines: list[str] = field(default_factory=list)
    suppression_lines: list[str] = field(default_factory=list)
    notification_lines: list[str] = field(default_factory=list)
    heartbeat_line: str = ""


def print_verbose_report(report: _Report) -> None:
    """Print structured diagnostic output to stdout."""
    sections = [
        ("[CONFIG]",            report.config_lines),
        ("[TARGET FILES]",      report.target_lines),
        ("[SUPPRESSION CHECK]",
         report.suppression_lines or ["  (no changes detected)"]),
        ("[NOTIFICATIONS]",
         report.notification_lines or ["  (no notifications sent)"]),
        ("[HEARTBEAT]",
         [report.heartbeat_line] if report.heartbeat_line else ["  (disabled)"]),
    ]
    print(file=sys.stdout)
    for header, lines in sections:
        print(header, file=sys.stdout)
        for line in lines:
            print(line, file=sys.stdout)
        print(file=sys.stdout)
