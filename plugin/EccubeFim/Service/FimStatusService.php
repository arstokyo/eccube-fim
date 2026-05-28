<?php
declare(strict_types=1);

namespace Plugin\EccubeFim\Service;

class FimStatusService extends StatusJsonService
{
    private const DEFAULT_INTERVAL_SECS = 15 * 60;  // fallback when timer_interval_secs absent

    public function getStatus(): array
    {
        $r = $this->tryReadJson();
        if (!$r['ok']) {
            $errorKey = 'eccube_fim.error.' . ($r['error'] ?? 'file_unreadable');
            return ['available' => false, 'error' => $errorKey];
        }
        return $this->enrich($r['data']);
    }

    protected function enrich(array $data): array
    {
        $data['available'] = true;
        $now = time();

        // threshold = 2 × timer interval; status.json carries the actual interval written by daemon
        $staleSecs = (int)($data['timer_interval_secs'] ?? self::DEFAULT_INTERVAL_SECS) * 2;

        if (isset($data['generated_at'])) {
            $age = $now - (int)$data['generated_at'];
            $data['generated_at_fmt']  = $this->fmtTs((int)$data['generated_at']);
            $data['generated_age_fmt'] = $this->fmtAge($age);
            $data['status_stale']      = $age > $staleSecs;
        }

        if (isset($data['heartbeat']['last_seen_at'])) {
            $data['heartbeat']['last_seen_fmt'] = $this->fmtTs((int)$data['heartbeat']['last_seen_at']);
        }

        foreach ($data['recent_detections'] ?? [] as $i => $det) {
            if (isset($det['detected_at'])) {
                $data['recent_detections'][$i]['detected_at_fmt'] = $this->fmtTs((int)$det['detected_at']);
            }
        }

        return $data;
    }
}
