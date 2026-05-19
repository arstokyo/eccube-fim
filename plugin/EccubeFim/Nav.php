<?php
declare(strict_types=1);

namespace Plugin\EccubeFim;

use Eccube\Common\EccubeNav;

class Nav implements EccubeNav
{
    public static function getNav(): array
    {
        return [
            'eccube_fim' => [
                'name' => 'FIM監視',
                'icon' => 'fa-shield-alt',
                'children' => [
                    'eccube_fim_monitor' => [
                        'name' => 'ダッシュボード',
                        'url'  => 'plugin_eccube_fim_admin_monitor',
                    ],
                ],
            ],
        ];
    }
}
