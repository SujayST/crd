# crd_question_generator.py

import random
import re
import requests
import datetime
from typing import Dict, List

from helper import get_templates, build_topic_summary, push_sme_questions_to_bank

# ================= CONFIG =================

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "openhermes"

RAW_QUESTIONS_PER_TOPIC = 14
FINAL_MIN_QUESTIONS = 5
FINAL_MAX_QUESTIONS = 8

MAX_CONTEXT_CHARS = 2500

# ================= SUBJECT EXTRACTION =================

def extract_subject(text: str) -> str:
    if not text:
        return "this design aspect"

    text = re.sub(r"\s+", " ", text.strip())
    text = re.sub(r"^\s*\d+[\.\)]\s*", "", text)

    anchors = [
        "migration", "design", "architecture", "scenario",
        "segment routing", "bgp", "isis", "evpn", "l3vpn"
    ]

    text_lc = text.lower()
    for a in anchors:
        if a in text_lc:
            text = text[text_lc.find(a):]
            break

    text = re.split(
        r"(which|that|where|who|when|how|regarding|with respect to)",
        text,
        flags=re.IGNORECASE
    )[0]

    words = text.split()
    return " ".join(words[:20]) if len(words) >= 3 else "this design aspect"


# ================= DESIGN SIGNAL DETECTOR =================

def detect_signals(text: str) -> Dict:
    t = text.lower()

    return {
        "migration": any(x in t for x in ["migration", "migrate", "coexist"]),
        "segment_routing": any(x in t for x in ["sr", "segment routing", "ti-lfa"]),
        "bgp": "bgp" in t,
        "evpn": "evpn" in t,
        "scale": bool(re.search(r"\b\d{3,}\b", t)),
        "resiliency": any(x in t for x in ["failover", "redundancy", "protection"]),
        "multidomain": "multi" in t and "domain" in t,
    }


# ================= SMART TEMPLATE PICKER =================

def pick_template(templates: List[str], signals: Dict) -> str:
    priority = []

    if signals["migration"]:
        priority += [t for t in templates if "migration" in t.lower()]

    if signals["scale"]:
        priority += [t for t in templates if "scale" in t.lower()]

    if signals["resiliency"]:
        priority += [t for t in templates if any(x in t.lower() for x in ["resilien", "fail", "redundan"])]

    if signals["bgp"]:
        priority += [t for t in templates if "bgp" in t.lower()]

    if priority:
        return random.choice(priority)

    return random.choice(templates)


# ================= LLM REFINER =================

def split_compound_questions(q: str) -> List[str]:
    """
    Splits multiple questions in one line into separate questions.
    Keeps only meaningful architect-level questions.
    """

    # Split by question mark
    parts = re.split(r"\?\s*", q)

    clean_parts = []
    for p in parts:
        p = p.strip()

        if not p:
            continue

        # Add ? back
        if not p.endswith("?"):
            p += "?"

        # ignore too short junk
        if len(p.split()) < 5:
            continue

        clean_parts.append(p)

    return clean_parts


def call_llm_refiner(topic: str, summary: List[str], questions: List[str], context: str) -> List[str]:

    prompt = f"""
You are a PRINCIPAL telecom network architect reviewing a CRD for production deployment.

Your job:
Identify missing design validations, migration risks, scale risks, resiliency gaps and operational clarity questions.
STRICT RULE:
Each numbered item must contain ONLY ONE question.
Do not combine multiple questions in one line.
Topic:
{topic}

Authoritative CRD summary (do NOT contradict):
{chr(10).join(f"- {s}" for s in summary)}

Evidence context:
{context}

Draft clarification questions:
{chr(10).join(f"{i+1}. {q}" for i, q in enumerate(questions))}

Instructions:
- Remove weak or generic questions
- Merge duplicates
- Make questions architect-level and design-specific
- Focus on migration, scale, resiliency, interoperability and operations
- Do NOT invent facts not in CRD
- Keep questions precise and technical
- Return ONLY numbered questions
- Return {FINAL_MIN_QUESTIONS} to {FINAL_MAX_QUESTIONS} questions
"""

    r = requests.post(
        OLLAMA_URL,
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                    "temperature": 0.1,
                    "num_predict": 350,
                    "num_ctx": 2048,
                    "num_thread": 4
                }

        },
        timeout=600
    )

    r.raise_for_status()
    lines = r.json()["response"].split("\n")

    cleaned = []

    for l in lines:
        l = l.strip()

        if not l or not l[0].isdigit():
            continue

        q = l.lstrip("0123456789. ").strip()

        # split multi-questions
        split_qs = split_compound_questions(q)

        cleaned.extend(split_qs)

    # remove duplicates while preserving order
    seen = set()
    final = []
    for q in cleaned:
        if q not in seen:
            seen.add(q)
            final.append(q)

    return final




# ================= MAIN GENERATOR =================

def generate_questions_json(session, domain="sp", segment="routing") -> Dict:

    output = {
        "generated_at": datetime.datetime.utcnow().isoformat(),
        "domain": domain,
        "segment": segment,
        "topics": {}
    }

    topics = session.run("""
        MATCH (t:Topic)
        RETURN DISTINCT toLower(t.name) AS topic
        ORDER BY topic
    """).value()

    for topic in topics:

        templates = get_templates(topic, domain, segment)

        if not templates:
            templates = [
                "What design assumptions exist for {subject}?",
                "What migration or rollback risks exist for {subject}?",
                "Are there scale or resiliency risks for {subject}?",
                "Does {subject} require validation with customer?"
            ]

        summary = build_topic_summary(session, topic)

        raw_questions = []
        context_blocks = []

        chunks = session.run("""
            MATCH (t:Topic)
            WHERE toLower(t.name) = $topic
            MATCH (t)<-[:BELONGS_TO]-(c:Chunk)
            RETURN c.text AS text
        """, topic=topic)

        for row in chunks:
            text = row["text"]

            subject = extract_subject(text)
            signals = detect_signals(text)
            template = pick_template(templates, signals)

            try:
                q = template.format(subject=subject)
            except Exception:
                q = template

            raw_questions.append(q)
            context_blocks.append(text[:400])

            if len(raw_questions) >= RAW_QUESTIONS_PER_TOPIC:
                break

        raw_questions = list(dict.fromkeys(raw_questions))
        if not raw_questions:
            continue

        refined = call_llm_refiner(
            topic,
            summary,
            raw_questions,
            "\n\n".join(context_blocks)[:MAX_CONTEXT_CHARS]
        )

        if len(refined) < FINAL_MIN_QUESTIONS:
            refined.extend(q for q in raw_questions if q not in refined)

        refined = refined[:FINAL_MAX_QUESTIONS]

        output["topics"][topic] = {
            "generated_questions": refined,
            "status": "pending_sme_review"
        }

    return output
