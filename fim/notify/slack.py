import json
import logging
import urllib.request
from pathlib import Path

from fim.config import NotifySlack

log = logging.getLogger(__name__)

_SLACK_HTTP_TIMEOUT = 15


class SlackChannel:
    """Sends alert notifications to one or more Slack webhooks."""

    def __init__(self, cfg: NotifySlack) -> None:
        self._cfg = cfg

    def send(self, hostname: str, detection: dict) -> bool:
        if not self._cfg.webhook_url_files:
            log.warning("No Slack webhook files configured — skipping Slack")
            return False
        results = []
        for wh_file in self._cfg.webhook_url_files:
            if not Path(wh_file).exists():
                log.warning("Slack webhook file not found: %s", wh_file)
                results.append(False)
                continue
            try:
                webhook = Path(wh_file).read_text(encoding="utf-8").strip()
                _post_webhook(webhook, hostname, detection)
                results.append(True)
            except Exception as e:
                log.error("Slack send failed (%s): %s", wh_file, e)
                results.append(False)
        return all(results)


def _post_webhook(webhook: str, hostname: str, detection: dict) -> None:
    from fim.template import render_body
    text = render_body(hostname, detection)
    payload = json.dumps({"text": text}).encode("utf-8")
    req = urllib.request.Request(
        webhook, data=payload,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=_SLACK_HTTP_TIMEOUT) as resp:
        log.info("Slack sent (HTTP %d)", resp.status)
