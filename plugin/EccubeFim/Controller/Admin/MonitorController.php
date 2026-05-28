<?php
declare(strict_types=1);

namespace Plugin\EccubeFim\Controller\Admin;

use Plugin\EccubeFim\Service\FimStatusService;
use Plugin\EccubeFim\Service\MalwareStatusService;
use Symfony\Bundle\FrameworkBundle\Controller\AbstractController;
use Symfony\Component\Routing\Annotation\Route;
use Sensio\Bundle\FrameworkExtraBundle\Configuration\Template;

class MonitorController extends AbstractController
{
    private FimStatusService $fimService;
    private MalwareStatusService $malwareService;

    public function __construct(
        FimStatusService $fimService,
        MalwareStatusService $malwareService
    ) {
        $this->fimService     = $fimService;
        $this->malwareService = $malwareService;
    }

    /**
     * @Route("/%eccube_admin_route%/fim", name="plugin_eccube_fim_admin_monitor", methods={"GET"})
     *
     * @Template("@EccubeFim/admin/EccubeFim/index.twig")
     */
    public function index(): array
    {
        return [
            'status'         => $this->fimService->getStatus(),
            'malware_status' => $this->malwareService->getStatus(),
        ];
    }
}
