import sys
import pytest
from unittest.mock import patch

from fim.cli import main


@pytest.mark.parametrize("argv", [
    ["eccube-fim", "check"],
    ["eccube-fim", "validate"],
    ["eccube-fim", "test", "mail"],
    ["eccube-fim", "test", "slack"],
    ["eccube-fim", "approve", "app/template/default/Shopping/index.twig"],
    ["eccube-fim", "upgrade"],
    ["eccube-fim", "uninstall"],
])
def test_command_fails_when_not_root(monkeypatch, capsys, argv):
    monkeypatch.setattr("os.geteuid", lambda: 1000)
    with patch.object(sys, "argv", argv):
        result = main()
    assert result == 1
    assert "root" in capsys.readouterr().err


@pytest.mark.parametrize("argv,mock_target,mock_return", [
    (["eccube-fim", "check"], "fim.cli.cmd_check", 0),
    (["eccube-fim", "validate"], "fim.cli.cmd_validate", 0),
    (["eccube-fim", "test", "mail"], "fim.cli_parsers_test.cmd_test_mail", 0),
    (["eccube-fim", "test", "slack"], "fim.cli_parsers_test.cmd_test_slack", 0),
    (["eccube-fim", "approve", "app/template/default/Shopping/index.twig"],
     "fim.cli.cmd_approve", 0),
    (["eccube-fim", "upgrade"], "fim.cli.cmd_upgrade", 0),
    (["eccube-fim", "uninstall"], "fim.cli.cmd_uninstall", 0),
])
def test_command_proceeds_when_root(monkeypatch, tmp_path, argv, mock_target, mock_return):
    monkeypatch.setattr("os.geteuid", lambda: 0)
    # prevent setup_logging() from opening /var/log/eccube-fim/check.log
    monkeypatch.setattr("fim.log.LOG_DIR", tmp_path / "log")
    (tmp_path / "daemon.yaml").write_text("root_path: /tmp\n")
    (tmp_path / "targets.yaml").write_text("target_files:\n  - index.twig\n")
    (tmp_path / "notify.yaml").write_text("email:\n  smtp_host: localhost\n")
    with patch.object(sys, "argv", ["eccube-fim", "--config-dir", str(tmp_path)] + argv[1:]):
        with patch(mock_target, return_value=mock_return) as mock_fn:
            result = main()
    assert mock_fn.called
    assert result == mock_return
