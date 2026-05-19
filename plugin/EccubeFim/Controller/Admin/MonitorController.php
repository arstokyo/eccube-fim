<?php
declare(strict_types=1);

namespace Plugin\EccubeFim\Controller\Admin;

use Plugin\EccubeFim\Service\FimStatusService;
use Symfony\Bundle\FrameworkBundle\Controller\AbstractController;
use Symfony\Component\Routing\Annotation\Route;
use Sensio\Bundle\FrameworkExtraBundle\Configuration\Template;

class MonitorController extends AbstractController
{
    private FimStatusService $fimService;

    public function __construct(FimStatusService $fimService)
    {
        $this->fimService = $fimService;
    }

    /**
     * @Route("/%eccube_admin_route%/fim", name="plugin_eccube_fim_admin_monitor", methods={"GET"})
     * 
     * @Template("@EccubeFim/admin/EccubeFim/index.twig")
     */
    public function index()
    {
        return [
            'status' => $this->fimService->getStatus(),
        ];
    }
}
