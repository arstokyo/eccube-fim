import logging
from unittest.mock import patch
from fim.log import setup_logging


def _reset_logger():
    logger = logging.getLogger("eccube-fim")
    logger.handlers.clear()


def test_setup_logging_adds_file_handler_when_dir_exists(tmp_path, monkeypatch):
    monkeypatch.setattr("fim.log.LOG_DIR", tmp_path)
    _reset_logger()
    setup_logging()
    logger = logging.getLogger("eccube-fim")
    handler_types = [type(h).__name__ for h in logger.handlers]
    assert "FileHandler" in handler_types


def test_setup_logging_warns_when_file_handler_fails(tmp_path, monkeypatch, caplog):
    monkeypatch.setattr("fim.log.LOG_DIR", tmp_path)
    _reset_logger()
    with patch("logging.FileHandler", side_effect=OSError("permission denied")):
        with caplog.at_level(logging.WARNING, logger="eccube-fim"):
            setup_logging()
    assert "Cannot write to log file" in caplog.text


def test_setup_logging_always_adds_stderr_handler(tmp_path, monkeypatch):
    monkeypatch.setattr("fim.log.LOG_DIR", tmp_path)
    _reset_logger()
    with patch("logging.FileHandler", side_effect=OSError("no such file")):
        setup_logging()
    logger = logging.getLogger("eccube-fim")
    stream_handlers = [h for h in logger.handlers if isinstance(h, logging.StreamHandler)
                       and not isinstance(h, logging.FileHandler)]
    assert len(stream_handlers) == 1
