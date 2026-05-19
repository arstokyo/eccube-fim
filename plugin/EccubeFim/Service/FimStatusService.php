<?php
declare(strict_types=1);

namespace Plugin\EccubeFim\Service;

class FimStatusService
{
    private const DEFAULT_INTERVAL_SECS = 15 * 60;  // fallback when timer_interval_secs absent

    private string $statusFile;

    public function __construct(string $statusFile)
    {
        $this->statusFile = $statusFile;
    }

    public function getStatus(): array
    {
        if (!is_readable($this->statusFile)) {
            return [
                'available' => false,
                'error'     => 'eccube_fim.error.file_unreadable',
            ];
        }

        $content = file_get_contents($this->statusFile);
        if ($content === false) {
            return ['available' => false, 'error' => 'eccube_fim.error.file_read_failed'];
        }

        $data = json_decode($content, true);
        if (!is_array($data)) {
            return ['available' => false, 'error' => 'eccube_fim.error.invalid_format'];
        }

        return $this->enrich($data);
    }

    private function enrich(array $data): array
    {
        $data['available'] = true;
        $now = time();

        // threshold = 2 × timer interval; status.json carries the actual interval written by daemon
        $staleSecs = (int)($data['timer_interval_secs'] ?? self::DEFAULT_INTERVAL_SECS) * 2;

        if (isset($data['generated_at'])) {
            $age = $now - (int) $data['generated_at'];
            $data['generated_at_fmt']  = $this->fmtTs((int) $data['generated_at']);
            $data['generated_age_fmt'] = $this->fmtAge($age);
            $data['status_stale']      = $age > $staleSecs;
        }

        if (isset($data['heartbeat']['last_seen_at'])) {
            $data['heartbeat']['last_seen_fmt'] = $this->fmtTs((int) $data['heartbeat']['last_seen_at']);
        }

        foreach ($data['recent_detections'] ?? [] as &$det) {
            if (isset($det['detected_at'])) {
                $det['detected_at_fmt'] = $this->fmtTs((int) $det['detected_at']);
            }
        }
        unset($det);

        return $data;
    }

    private function fmtTs(int $ts): string
    {
        return date('Y-m-d H:i:s', $ts);
    }

    private function fmtAge(int $secs): string
    {
        if ($secs < 60)  return "{$secs}秒前";
        $m = intdiv($secs, 60);
        if ($m < 60)     return "{$m}分前";
        return intdiv($m, 60) . '時間前';
    }
}
