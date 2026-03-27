from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .services.pipelines import ingest_crd_documents, ingest_customer_excel
from .services.bank import ingest_sme_questions


class HealthView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return Response({"status": "ok"})

test_data = {
  "generated_at": "2026-02-06T12:15:01.171482",
  "domain": "sp",
  "segment": "routing",
  "topics": {
    "architecture": {
      "generated_questions": [
        "What specific assumptions are being made in the design regarding the number of eNodeBs per PoP, access rings, pre-aggregation rings, core routers, and SAR nodes, which must be explicitly validated with the customer?",
        "Does this design aspect require updates or exceptions in the existing HLD (High-Level Description) or LLD (Low-Level Description) assumptions related to topology, scale, or capacity?",
        "What are the specific migration plans for the TI-LFA protocol, and how will it impact the existing HLD or LLD assumptions regarding routing protocols and network operations?",
        "Are there any deviations in the proposed design from the baseline design that require updates or exceptions in the existing HLD or LLD assumptions, such as topology, scale, or capacity?",
        "How does the proposed layer-based reference-bandwidth approach for each layer of CEN align with the customer's requirements, and what are the implications for network operations and performance?",
        "What are the specific benefits and drawbacks of moving to TI-LFA from RLFA in the access layer, and how will this impact the existing HLD or LLD assumptions regarding routing protocols and network operations?"
      ],
      "status": "pending_sme_review"
    },
    "bgp": {
      "generated_questions": [
        "Can you confirm that the BGP design assumption for Scenario Pre-Agg is a mesh connectivity architecture, where each Pre-Aggrouter is connected to two Core/Agg routers?",
        "How does the current routing architecture align with the use of EVPN AFI in the FLDS core network, and what are the implications for address families such as IPv4, L2VPN, and IPv6-LU?",
        "What is the expected failover time without a convergence mechanism, and how does the BGP PIC solution address this issue?",
        "How will the migration of RR devices from MX104 to MX240 in Kerala and MX480 in Rajasthan impact the overall routing architecture, and what are the implications for services and BGP-LU routes?",
        "Can you clarify why the access ring is terminating on Pre-agg in one end and core in another end, and how this affects the BGP LU route distribution between the two?",
        "How will the change from a Circle RR to an Agg/Core router as an inline RR (Ring split activity) impact the routing architecture, and what are the implications for BGP-LU routes and next-hop self?"
      ],
      "status": "pending_sme_review"
    },
    "ems-paragon": {
      "generated_questions": [
        "What is the expected EMS scope, feature set, and operational requirements for design documents (e.g., BoQ) and network deployment documents (NDD), and how will these be reflected in the Paragon EMS & PID+NDD Automation?",
        "How will the automation of NDD creation be achieved, and what APIs or interfaces will be used to facilitate this process?",
        "What is the expected workflow for site surveys, and how will inputs from PID documents influence this process?",
        "Can you confirm that internet connectivity on devices will be disconnected after configuration push, and if so, what are the implications for device management and maintenance?",
        "How will comparative studies between Paragon EMS & PID+NDD Automation and existing systems be conducted, and what metrics or KPIs will be used to evaluate its effectiveness?"
      ],
      "status": "pending_sme_review"
    },
    "hardware- software": {
      "generated_questions": [
        "Does the proposed multi-instance ISIS approach require interoperability testing to ensure seamless ring termination between different layers, and if so, what specific tests need to be conducted?",
        "Are there any platform-specific validation requirements for the JunOS software version (21.2R3-S8) needed for multi-instance ISIS on RE1800 devices, and if so, how will they impact the design?",
        "How does the proposed use of separate software versions (23.X Core and Agg router) for NG-RE and other components affect the overall system resiliency and scalability?",
        "What are the implications of removing existing RIB group-based leaking mechanisms after migrating to multi-instance, and how will this impact network operations?",
        "Are there any specific requirements or recommendations for Segment Routing (SR) implementation in the access/pre-aggregation layers, and if so, how will they be integrated with SR TE in the core/agg layer?",
        "How will the proposed BGP design approach address the requirement for a layer-based metric for each of the CEN layers with reference bandwidth, particularly when ring termination occurs between different layers?"
      ],
      "status": "pending_sme_review"
    },
    "igp, mpls, sr": {
      "generated_questions": [
        "Are there any fast convergence, protection, or resiliency mechanisms required specifically for full mesh SR-TE in Core/Agg sites?",
        "What assumptions are being made about metrics, reference bandwidth, and label/SID allocation for Design does not have to cover mobility traffic or business services crossing the core to other circles?",
        "Are there any scalability concerns with using LDP + SR in this design aspect?",
        "Does this design aspect introduce any operational risks under peak or failure scenarios, such as loss of SR-TE connectivity?",
        "Is additional validation or lab testing required for this design aspect during migration to ensure compatibility with Juniper devices?"
      ],
      "status": "pending_sme_review"
    },
    "miscellaneous": {
      "generated_questions": [
        "Will the Bi-Di SFP configuration impact OSS/BSS integration, monitoring, or operational processes?",
        "Confirm whether Dual Stack - Loopbacks are dual stack. WAN link IPv6 will be enabled later once the future state follows existing standards or requires new guidelines or exceptions.",
        "Are there any open assumptions, dependencies, or risks related to Layer Top 50 city Below Top 50 city RoN ( Rest of Network) Core/Agg nX100G (Optics)?",
        "Will the migration phase impact management services such as V4 & V6 connections?",
        "Confirm whether the termination of rings across any layer will be terminated in separate ISIS instances.",
        "Are there any open assumptions, dependencies, or risks related to scenarios common to all circles but call out?"
      ],
      "status": "pending_sme_review"
    },
    "qos": {
      "generated_questions": [
        "Does the customer require any changes to the classification rules or marking of traffic for Feature \u2013 QoS, given that no change is confirmed?",
        "Are there any scheduling requirements or behavior modifications needed for Feature \u2013 QoS on Evo-based platforms, considering only basic monitoring is required?",
        "How will the QoS feature be handled during migration from Junos platforms to Evo-based platforms, and are there any specific resiliency considerations?",
        "What impact will the introduction of QoS have on operations, particularly in terms of monitoring and troubleshooting, on Evo-based platforms?",
        "Are there any scalability implications or performance considerations that need to be addressed for Feature \u2013 QoS on Evo-based platforms?"
      ],
      "status": "pending_sme_review"
    },
    "services": {
      "generated_questions": [
        "Does the proposed design require hub-and-spoke, full-mesh, or any-to-any connectivity for the Pre-Agg ring (Pre-Agg 1B) from RoN pre-agg ring for access ring termination at which layers?",
        "Are there specific requirements for PTN to eNodeB (eNB) connectivity in terms of VRFs, VLANs, and service termination points that need to be documented?",
        "How will the Core capacity = 800G and Agg Capacity = 200G core and aggregation difference impact the overall design and scalability of the network?",
        "Are there any specific protocols or features proposed for new services (Radio - Enterprise) that require pre-approval from the customer for readiness planning?",
        "How will the separation of management VPNs for each radio service be implemented, and what are the implications for VPN termination and access node usage?",
        "What is the plan for managing microwave management (UBR) gateway migration to the new access/pre-agg devices, and how will this impact overall network operations?"
      ],
      "status": "pending_sme_review"
    },
    "use cases": {
      "generated_questions": [
        "What specific network topology and device configurations must be met before executing Scenario a. LDP --> SR, to ensure seamless migration to Juniper's SR?",
        "What are the necessary network protocols and services that need to be enabled or configured for Use Case b. Non-Juniper --> Juniper, to facilitate a smooth transition from non-Juniper devices to Juniper equipment?",
        "What are the key performance indicators (KPIs) and monitoring metrics that must be in place before executing Scenario a. LDP --> SR, to ensure optimal network performance and reliability?",
        "How do the existing network infrastructure and device configurations impact the feasibility of Use Case c. New ring greenfield deployment, and what modifications or upgrades are required to support this scenario?"
      ],
      "status": "pending_sme_review"
    }
  }
}


class CRDDocIngestView(APIView):
    """
    POST multipart with files[], project_id, optional domain/segment.
    """

    def post(self, request):
        project_id = request.data.get("project_id")
        domain = (request.data.get("domain") or settings.DOMAIN_DEFAULT).lower().strip()
        segment = (request.data.get("segment") or settings.SEGMENT_DEFAULT).lower().strip()

        project_name = request.data.get("project_name") or project_id

        files = request.FILES.getlist("files")
        if not files and request.FILES.get("file"):
            files = [request.FILES["file"]]

        if not project_id or not files:
            return Response(
                {"error": "project_id and at least one uploaded file are required (use 'files' or 'file')"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = ingest_crd_documents(files, project_id, domain, segment, project_name)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        # result = test_data

        return Response(result, status=status.HTTP_201_CREATED)


class CustomerExcelIngestView(APIView):
    """
    POST multipart with file, project_id, optional domain/segment.
    """

    def post(self, request):
        project_id = request.data.get("project_id")
        domain = (request.data.get("domain") or settings.DOMAIN_DEFAULT).lower().strip()
        segment = (request.data.get("segment") or settings.SEGMENT_DEFAULT).lower().strip()

        file_obj = request.FILES.get("files")
        if not project_id or not file_obj:
            return Response(
                {"error": "project_id and file are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            audit_json = ingest_customer_excel(file_obj, project_id, domain, segment)
        except Exception as e:
            return Response({"errorr": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(audit_json, status=status.HTTP_201_CREATED)


class SMEQuestionsIngestView(APIView):
    """
    POST JSON body matching push_sme_questions_to_bank schema.
    {
      "domain": "...",
      "segment": "...",
      "topics": {
         "topic1": { "approved_questions": [...] },
         ...
      }
    }
    """

    def post(self, request):
        if not isinstance(request.data, dict):
            return Response({"error": "JSON body required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            result = ingest_sme_questions(request.data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(result, status=status.HTTP_201_CREATED)
