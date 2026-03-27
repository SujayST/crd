from helper import add_template

# ==========================================
# CHANGE THESE ONLY IF NEEDED
# ==========================================

DOMAIN = "sp"
SEGMENT = "routing"

# ==========================================
# MASTER TEMPLATE MAP
# ==========================================

TEMPLATE_MAP = {

    "Use cases": [
        "Confirm the scope of {subject} across all circles and identify any circle-specific deviations.",
        "Which rollout phases does {subject} apply to (greenfield, brownfield, migration), and in what sequence?",
        "What dependencies, prerequisites, or readiness criteria must be met before executing {subject}?",
        "Are there any migration risks, service-impact scenarios, or rollback constraints associated with {subject}?",
        "Is {subject} aligned with the overall rollout priority, deployment sequencing, and migration strategy?",
        "Are there any assumptions in {subject} that require validation before finalizing the design?"
    ],

    "Architecture": [
        "Confirm whether the proposed {subject} aligns with the standard access, pre-aggregation, and aggregation architecture.",
        "Are there any deviations in topology, scale, or capacity for {subject} compared to the baseline design?",
        "How does {subject} impact redundancy, resiliency, failure domains, and fault isolation?",
        "Are there any non-standard scenarios, corner cases, or exception flows related to {subject} that must be documented?",
        "Does {subject} require updates or exceptions in the existing HLD or LLD assumptions?",
        "What specific assumptions are being made in {subject}, and which of them must be explicitly validated with the customer?",
        "Are there any scale limits, boundaries, or sizing numbers missing for {subject} that need to be documented?"
    ],

    "IGP, MPLS, SR": [
        "Confirm the detailed design approach for {subject} and whether it differs from the existing network implementation.",
        "Will {subject} coexist with legacy mechanisms during migration? If yes, for how long and under what conditions?",
        "Are there any fast convergence, protection, or resiliency mechanisms required specifically for {subject}?",
        "Does {subject} introduce any scalability, convergence, or operational risks under peak or failure scenarios?",
        "Is additional validation, lab testing, or phased rollout required for {subject} during migration?",
        "What assumptions are being made for metrics, reference bandwidth, or label/SID allocation for {subject}?",
        "What rollback or fallback mechanism exists if {subject} does not behave as expected during migration?"
    ],

    "BGP": [
        "Confirm the BGP design assumptions for {subject} and validate alignment with the overall routing architecture.",
        "Does {subject} require additional BGP address families, policies, communities, or route filtering?",
        "How does {subject} impact the route-reflector hierarchy, convergence behavior, and scaling limits?",
        "Are there any migration, coexistence, or temporary exception scenarios related to {subject}?",
        "Is BGP PIC, AIGP, Anycast-SID, or authentication required for {subject}, and what are the trade-offs?",
        "What steady-state and failure-state route scale is expected for {subject}?"
    ],

    "Services": [
        "Confirm whether {subject} is supported as per the existing service model or requires new service definitions.",
        "How is traffic for {subject} expected to flow across access, aggregation, and core layers?",
        "Does {subject} require hub-and-spoke, full-mesh, or any-to-any connectivity, and at which layers?",
        "Are there any IPv6, dual-stack, or future service considerations associated with {subject}?",
        "Are there any special migration, coexistence, or service continuity requirements for {subject}?",
        "Does {subject} introduce new VRFs, VLANs, or service termination points that must be documented?"
    ],

    "Hardware- Software": [
        "Confirm whether the proposed hardware and software combination for {subject} is final and fully supported.",
        "Are there any known feature gaps, scale limitations, or hardware constraints related to {subject}?",
        "Does {subject} require interoperability testing, hardware qualification, or platform-specific validation?",
        "Is the proposed software release for {subject} aligned with the long-term support and upgrade strategy?",
        "Are there any hardware refresh, RE, MPC, or line-card dependency considerations associated with {subject}?"
    ],

    "QoS": [
        "Confirm whether {subject} remains unchanged from the existing QoS design.",
        "Is there any requirement to revisit classification, marking, scheduling, or rewrite behavior for {subject}?",
        "Are there any congestion management, queuing, or WRED/RED considerations related to {subject}?",
        "Does {subject} introduce any new SLA, priority, or service differentiation requirements?"
    ],

    "Scaling and Performance": [
        "What are the expected scale limits for {subject} in terms of routes, interfaces, tunnels, or services?",
        "Are growth projections and traffic forecasts validated against current hardware capabilities for {subject}?",
        "Are there any high-availability, protection, or redundancy requirements specific to {subject}?",
        "What performance benchmarks, KPIs, or acceptance criteria are expected for {subject}?"
    ],

    "EMS-Paragon": [
        "Confirm the EMS scope, feature set, and operational requirements for {subject}.",
        "Does {subject} require automation workflows, telemetry integration, or closed-loop operations?",
        "Are there any licensing, sizing, deployment, or HA considerations associated with {subject}?",
        "What manual versus automated inputs are expected for {subject} during onboarding and provisioning?"
    ],

    "Miscellaneous": [
        "Confirm whether {subject} follows existing standards or requires new guidelines or exceptions.",
        "Are there any open assumptions, dependencies, or risks related to {subject}?",
        "Does {subject} impact OSS/BSS integration, monitoring, or operational processes?",
        "Are there any ownership, responsibility, or handoff considerations associated with {subject}?"
    ]
}

# ==========================================
# UPLOAD LOGIC
# ==========================================

print("\n🚀 Starting template upload to Chroma...\n")

total = 0

for topic, template_list in TEMPLATE_MAP.items():

    topic_clean = topic.lower().strip()

    for template in template_list:

        if not template.strip():
            continue

        add_template(
            topic=topic_clean,
            template_text=template.strip(),
            domain=DOMAIN,
            segment=SEGMENT
        )

        total += 1

print(f"\n✅ SUCCESS: {total} templates uploaded into Chroma DB\n")
