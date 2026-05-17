import pytest
from fim.timer_ops import parse_interval_arg, format_interval


def test_parse_minutes():
    assert parse_interval_arg("5") == 5
    assert parse_interval_arg("30") == 30


def test_parse_hours():
    assert parse_interval_arg("1h") == 60


def test_parse_invalid():
    with pytest.raises(ValueError):
        parse_interval_arg("0")
    with pytest.raises(ValueError):
        parse_interval_arg("bad")
    with pytest.raises(ValueError):
        parse_interval_arg("1.5h")
    with pytest.raises(ValueError):
        parse_interval_arg("2h")
    with pytest.raises(ValueError):
        parse_interval_arg("61")


def test_format_minutes():
    assert format_interval(5) == "5m"
    assert format_interval(30) == "30m"
    assert format_interval(59) == "59m"


def test_format_hours():
    assert format_interval(60) == "1h"
