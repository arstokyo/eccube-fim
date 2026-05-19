<?php
declare(strict_types=1);

namespace Plugin\EccubeFim\Controller\Admin;

use Plugin\EccubeFim\Service\FimStatusService;
use Symfony\Bundle\FrameworkBundle\Controller\AbstractController;
use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\Routing\Annotation\Route;

class MonitorController extends AbstractController
{
    private FimStatusService $fimService;

    public function __construct(FimStatusService $fimService)
    {
        $this->fimService = $fimService;
    }

    /**
     * @Route("/%eccube_admin_route%/fim", name="plugin_eccube_fim_admin_monitor", methods={"GET"})
     */
    public function index(Request $request): Response
    {
        return $this->render('@EccubeFim/admin/EccubeFim/index.twig', [
            'status' => $this->fimService->getStatus(),
        ]);
    }
}
