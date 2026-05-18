import json
import logging
import urllib.request
from pathlib import Path

from fim.config import NotifySlack
from fim.notify.base import RenderedNotification

log = logging.getLogger(__name__)

_SLACK_HTTP_TIMEOUT = 15


class SlackChannel:
    """Sends alert notifications to one or more Slack webhooks."""

    def __init__(self, cfg: NotifySlack) -> None:
        self._cfg = cfg

    def send(self, notification: RenderedNotification) -> bool:
        if not self._cfg.webhook_url_files:
            log.warning("No Slack webhook files configured — skipping Slack")
            return False
        results = []
        for wh_file in self._cfg.webhook_url_files:
            p = Path(wh_file)
            if not p.exists():
                log.warning("Slack webhook file not found: %s", wh_file)
                results.append(False)
                continue
            try:
                webhook = p.read_text(encoding="utf-8").strip()
                _post_webhook(webhook, notification.bodies["slack"])
                results.append(True)
            except Exception as e:
                log.error("Slack send failed (%s): %s", wh_file, e)
                results.append(False)
        return all(results)


def _post_webhook(webhook: str, text: str) -> None:
    payload = json.dumps({"text": text}).encode("utf-8")
    req = urllib.request.Request(
        webhook, data=payload,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=_SLACK_HTTP_TIMEOUT) as resp:
        log.info("Slack sent (HTTP %d)", resp.status)
