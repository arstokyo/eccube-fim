from fim.config import NotifyEmail
from fim.notify import dispatch_notifications
from fim.notify.email import EmailChannel


def _detection():
    return {
        "path": "index.twig",
        "full_path": "/shop/index.twig",
        "root_path": "/shop",
        "git_status": " M index.twig",
        "diff": "+tampered",
        "mtime": "2026-05-15 12:00:00 JST",
        "sha256": "abc123",
    }


class DummyChannel:
    def __init__(self, result=True):
        self.result = result
        self.calls = []

    def send(self, hostname: str, detections: list[dict]) -> bool:
        self.calls.append((hostname, detections))
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

    monkeypatch.setattr("fim.notify.email._send_smtp", fake_send_smtp)

    assert EmailChannel(cfg).send("host-a", [_detection()]) is True
    assert sent["cfg"] is cfg
    assert "[ALERT]" in sent["subject"]
    assert "/shop/index.twig" in sent["body"]
    assert "+tampered" in sent["body"]


def test_email_channel_returns_false_on_failure(monkeypatch):
    cfg = NotifyEmail(smtp_host="smtp.example.test")

    def fail_send_smtp(email_cfg, subject, body):
        raise OSError("smtp down")

    monkeypatch.setattr("fim.notify.email._send_smtp", fail_send_smtp)

    assert EmailChannel(cfg).send("host-a", [_detection()]) is False


def test_dispatch_notifications_calls_each_channel_once_with_full_list():
    first = DummyChannel()
    second = DummyChannel()
    detections = [_detection(), dict(_detection(), path="admin.twig")]

    ok = dispatch_notifications([first, second], "host-a", detections, dry_run=False)

    assert ok is True
    assert len(first.calls) == 1
    assert len(second.calls) == 1
    assert first.calls[0] == ("host-a", detections)
    assert second.calls[0] == ("host-a", detections)


def test_dispatch_notifications_reports_channel_failure():
    ok = dispatch_notifications(
        [DummyChannel(result=True), DummyChannel(result=False)],
        "host-a",
        [_detection()],
        dry_run=False,
    )

    assert ok is False


def test_dispatch_notifications_dry_run_skips_channels():
    channel = DummyChannel()

    ok = dispatch_notifications([channel], "host-a", [_detection()], dry_run=True)

    assert ok is True
    assert channel.calls == []
