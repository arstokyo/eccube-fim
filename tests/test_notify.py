import pytest
from fim.config import Config, NotifyEmail, NotifySlack
from fim.notify import dispatch_notifications, build_channels, send_test_notification
from fim.notify.base import RenderedNotification
from fim.notify.email import EmailChannel
from fim.notify.slack import SlackChannel


@pytest.fixture
def make_config():
    def _make(email_enabled: bool, slack_enabled: bool) -> Config:
        return Config(
            root_path="/x",
            target_files=[],
            email=NotifyEmail(
                enabled=email_enabled,
                recipients=["a@b.com"],
                smtp_host="localhost",
                smtp_port=25,
                from_addr="fim@x.com",
                smtp_user="",
                smtp_password_file="",
            ),
            slack=NotifySlack(
                enabled=slack_enabled,
                webhook_url_files=[],
            ),
        )
    return _make


class DummyChannel:
    """Test double for Channel; records send() calls and returns a preset result."""

    def __init__(self, result=True):
        self.result = result
        self.calls = []

    def send(self, notification: RenderedNotification) -> bool:
        self.calls.append(notification)
        return self.result


def test_email_channel_sends_rendered_message(monkeypatch, tmp_path):
    sent = {}
    pw_file = tmp_path / "smtp-password"
    pw_file.write_text("secret\n", encoding="utf-8")
    cfg = NotifyEmail(
        smtp_host="smtp.example.test",
        smtp_user="fim",
        smtp_password_file=str(pw_file),
        from_addr="fim@example.test",
        recipients=["ops@example.test"],
    )

    def fake_send_smtp(email_cfg, subject, body):
        sent["cfg"] = email_cfg
        sent["subject"] = subject
        sent["body"] = body

    monkeypatch.setattr("common.notify.email._send_smtp", fake_send_smtp)

    notification = RenderedNotification(
        subject="[ALERT] host-a",
        bodies={"email": "/shop/index.twig was tampered\n+tampered"},
    )
    assert EmailChannel(cfg).send(notification) is True
    assert sent["cfg"] is cfg
    assert sent["subject"] == "[ALERT] host-a"
    assert "/shop/index.twig" in sent["body"]


def test_email_channel_returns_false_on_failure(monkeypatch):
    cfg = NotifyEmail(smtp_host="smtp.example.test")

    def fail_send_smtp(email_cfg, subject, body):
        raise OSError("smtp down")

    monkeypatch.setattr("common.notify.email._send_smtp", fail_send_smtp)

    notification = RenderedNotification(subject="[ALERT]", bodies={"email": "body"})
    assert EmailChannel(cfg).send(notification) is False


def test_dispatch_notifications_calls_each_channel_once_with_rendered_notification():
    first = DummyChannel()
    second = DummyChannel()

    ok = dispatch_notifications([first, second], "host-a", [], dry_run=False)

    assert ok is True
    assert len(first.calls) == 1
    assert len(second.calls) == 1
    # both channels received the same RenderedNotification object
    assert first.calls[0] is second.calls[0]


def test_dispatch_notifications_reports_channel_failure():
    ok = dispatch_notifications(
        [DummyChannel(result=True), DummyChannel(result=False)],
        "host-a", [], dry_run=False,
    )
    assert ok is False


def test_dispatch_notifications_dry_run_skips_channels():
    channel = DummyChannel()

    ok = dispatch_notifications([channel], "host-a", [], dry_run=True)

    assert ok is True
    assert channel.calls == []


def test_build_channels_email_only(make_config):
    """Only email channel built when slack disabled."""
    cfg = make_config(email_enabled=True, slack_enabled=False)
    channels = build_channels(cfg)
    assert len(channels) == 1
    assert isinstance(channels[0], EmailChannel)


def test_build_channels_slack_only(make_config):
    cfg = make_config(email_enabled=False, slack_enabled=True)
    channels = build_channels(cfg)
    assert len(channels) == 1
    assert isinstance(channels[0], SlackChannel)


def test_build_channels_both(make_config):
    cfg = make_config(email_enabled=True, slack_enabled=True)
    channels = build_channels(cfg)
    assert len(channels) == 2


def test_build_channels_none_returns_empty(make_config):
    """build_channels returns [] when all channels disabled; load_config guards enabled check."""
    cfg = make_config(email_enabled=False, slack_enabled=False)
    assert build_channels(cfg) == []


_FAKE_NOTIFICATION = RenderedNotification(subject="[TEST]", bodies={"email": "", "slack": ""})


def test_send_test_notification_email_only_skips_slack(make_config, monkeypatch):
    """channel_name='email' must not invoke SlackChannel even if enabled."""
    cfg = make_config(email_enabled=True, slack_enabled=True)
    slack_calls = []

    monkeypatch.setattr("fim.notify._render", lambda *a, **kw: _FAKE_NOTIFICATION)
    monkeypatch.setattr("common.notify.email._send_smtp", lambda *a, **kw: None)

    def fake_slack_send(self, notification):
        slack_calls.append(notification)
        return True

    monkeypatch.setattr("fim.notify.slack.SlackChannel.send", fake_slack_send)

    results = send_test_notification(cfg, "host-a", channel_name="email")

    assert "EmailChannel" in results
    assert "SlackChannel" not in results
    assert slack_calls == []


def test_send_test_notification_slack_only_skips_email(make_config, monkeypatch):
    """channel_name='slack' must not invoke EmailChannel even if enabled."""
    cfg = make_config(email_enabled=True, slack_enabled=True)
    cfg.slack.webhook_url_files = ["/tmp/fake"]
    email_calls = []

    monkeypatch.setattr("fim.notify._render", lambda *a, **kw: _FAKE_NOTIFICATION)

    def fake_smtp(email_cfg, subject, body):
        email_calls.append(subject)

    monkeypatch.setattr("common.notify.email._send_smtp", fake_smtp)
    monkeypatch.setattr("fim.notify.slack.SlackChannel.send", lambda self, n: True)

    results = send_test_notification(cfg, "host-a", channel_name="slack")

    assert "SlackChannel" in results
    assert "EmailChannel" not in results
    assert email_calls == []


def test_send_test_notification_no_filter_sends_all(make_config, monkeypatch):
    """With no channel_name, all enabled channels are exercised (existing behaviour)."""
    cfg = make_config(email_enabled=True, slack_enabled=True)
    cfg.slack.webhook_url_files = ["/tmp/fake"]

    monkeypatch.setattr("fim.notify._render", lambda *a, **kw: _FAKE_NOTIFICATION)
    monkeypatch.setattr("common.notify.email._send_smtp", lambda *a, **kw: None)
    monkeypatch.setattr("fim.notify.slack.SlackChannel.send", lambda self, n: True)

    results = send_test_notification(cfg, "host-a")

    assert "EmailChannel" in results
    assert "SlackChannel" in results
