<?php
declare(strict_types=1);

namespace Plugin\EccubeFim\Service;

abstract class StatusJsonService
{
    protected string $statusFile;

    public function __construct(string $statusFile)
    {
        $this->statusFile = $statusFile;
    }

    abstract public function getStatus(): array;

    abstract protected function enrich(array $data): array;

    /**
     * Read and decode the status JSON file.
     *
     * Returns ['ok' => true,  'data'    => array]  on success.
     * Returns ['ok' => false, 'missing' => true]   when file does not exist.
     * Returns ['ok' => false, 'missing' => false, 'error' => string] on read/decode error.
     */
    protected function tryReadJson(): array
    {
        if (!file_exists($this->statusFile)) {
            return ['ok' => false, 'missing' => true];
        }
        if (!is_readable($this->statusFile)) {
            return ['ok' => false, 'missing' => false, 'error' => 'file_unreadable'];
        }
        $content = file_get_contents($this->statusFile);
        if ($content === false) {
            return ['ok' => false, 'missing' => false, 'error' => 'file_read_failed'];
        }
        $data = json_decode($content, true);
        if (!is_array($data)) {
            return ['ok' => false, 'missing' => false, 'error' => 'invalid_format'];
        }
        return ['ok' => true, 'data' => $data];
    }

    protected function fmtTs(int $ts): string
    {
        return date('Y-m-d H:i:s', $ts);
    }

    protected function fmtAge(int $secs): string
    {
        if ($secs < 60)  return "{$secs}秒前";
        $m = intdiv($secs, 60);
        if ($m < 60)     return "{$m}分前";
        return intdiv($m, 60) . '時間前';
    }
}
