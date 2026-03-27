import pandas as pd
import json
from collections import defaultdict
import datetime
import requests
from pathlib import Path
import hashlib
import unicodedata
import re

# ================= CONFIG =================

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "openhermes"


# ================= TEXT UTILS =================

def clean(val):
    if pd.isna(val):
        return ""
    return str(val).strip()


def normalize_text(text):
    text = text.lower().strip()
    text = unicodedata.normalize('NFD', text)
    text = re.sub(r'\s+', ' ', text)
    return text.replace('\u200b', '').replace('\ufeff', '')


def generate_chunk_hash(project_id, domain, segment, topic, text):
    raw = f"{project_id}|{domain}|{segment}|{topic}|{normalize_text(text)}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# ================= EXCEL PARSER =================

def find_response_column(df):
    keywords = ["response", "answer", "remark", "customer", "client", "input"]

    for col in df.columns:
        if any(k in col.lower() for k in keywords):
            print(f"✅ Detected response column: {col}")
            return col

    print("⚠️ No response column found — using last column")
    return df.columns[-1]


def parse_customer_excel(excel_path):
    df = pd.read_excel(excel_path)
    response_col = find_response_column(df)

    parsed = []
    current_topic = None

    for _, row in df.iterrows():
        sno = clean(row.get("S.NO"))
        topic_col = clean(row.get("Requirements/Topic"))
        question = clean(row.get("Questions"))
        assumption = clean(row.get("Assumptions"))
        response = clean(row.get(response_col))

        if topic_col and not question:
            current_topic = topic_col.lower()
            continue

        if question:
            parsed.append({
                "topic": current_topic or "general",
                "sno": sno,
                "question": question,
                "assumption": assumption,
                "answer": response,
                "status": "answered" if response else "unanswered"
            })

    return parsed


# ================= LLM SUMMARY =================

def call_summary_llm(topic, answered, unanswered):
    prompt = f"""
You are a PRINCIPAL telecom solution architect reviewing a Customer Requirement Document (CRD).

IMPORTANT:
Treat all Q&A below as ONE combined design context for this topic.
Do NOT explain each answer individually.
Create a consolidated technical assessment.

Topic:
{topic}

CUSTOMER RESPONSES (authoritative):
{chr(10).join("- " + a for a in answered[:40])}

OPEN QUESTIONS / MISSING INPUTS:
{chr(10).join("- " + u for u in unanswered[:40])}

YOUR TASK:
Create a single consolidated CRD design assessment using ALL inputs together.

STRICT RULES:
- Do NOT explain Q&A one by one
- Do NOT define terms (like “Nokia is a vendor” etc)
- Do NOT write generic telecom theory
- Focus only on THIS design
- Infer architecture only if clearly implied
- Be concise and technical
- Think like reviewing for HLD approval

OUTPUT FORMAT (follow EXACTLY):

CONFIRMED DESIGN:
- Combined architecture decisions inferred from all inputs
- Vendor selections
- Connectivity model
- Any clear design direction

OPEN RISKS / GAPS:
- Missing data blocking HLD/LLD
- Ambiguities
- Dependencies not confirmed

DESIGN IMPACT:
- Migration risks
- Scale risks
- Operational risks
- Vendor/interop concerns

OVERALL STATUS:
CLEAR / PARTIAL / HIGH RISK
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
    return r.json()["response"].strip()



def call_followup_llm(topic, summary_text, answered, unanswered):
    prompt = f"""
You are a senior telecom solution architect reviewing a CRD.

Topic: {topic}

CRD Summary:
{summary_text}

Answered Items:
{chr(10).join("- " + a for a in answered[:20])}

Unanswered Items:
{chr(10).join("- " + u for u in unanswered[:20])}

Your job:
Generate clarification questions ONLY where design is unclear,
risky, incomplete, or ambiguous.

Focus on:
- Missing architecture clarity
- Migration/rollback gaps
- Scale/performance limits
- Dependencies
- Operational risks
- Validation/signoff gaps

Rules:
- If design is fully clear → return NONE
- Otherwise return 3–6 sharp clarification questions
- Do NOT repeat existing questions
- Be specific and technical
- Return ONLY numbered questions
"""

    r = requests.post(
        OLLAMA_URL,
        json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
        timeout=600
    )

    r.raise_for_status()
    text = r.json()["response"].strip()

    if "NONE" in text.upper():
        return []

    return [
        l.strip().lstrip("0123456789. ")
        for l in text.split("\n")
        if l.strip() and l.strip()[0].isdigit()
    ]



# ================= INGEST INTO NEO4J =================

def ingest_iteration_chunks(builder, project_id, domain, segment, iteration_data):

    created = 0

    # 🔥 Auto-increment iteration from Segment
    iteration = builder.get_next_iteration(project_id, domain, segment)

    with builder.driver.session() as session:

        for topic, payload in iteration_data["topics"].items():

            topic_norm = normalize_text(topic)

            summary = payload["llm_summary"]
            raw_entries_json = json.dumps(payload["raw_entries"], indent=2)
            followups = payload["followup_questions"]

            chunk_text = f"""
ITERATION {iteration}

SUMMARY:
{summary}

FOLLOW-UP QUESTIONS:
{json.dumps(followups, indent=2)}

RAW Q&A:
{raw_entries_json}
"""

            chunk_hash = generate_chunk_hash(
                project_id, domain, segment, topic_norm, chunk_text
            )

            session.run(
                """
                MATCH (t:Topic {
                    name: $topic,
                    project_id: $project_id,
                    domain: $domain,
                    segment: $segment
                })

                MERGE (c:Chunk {
                    chunk_hash: $chunk_hash,
                    project_id: $project_id,
                    domain: $domain,
                    segment: $segment,
                    topic: $topic,
                    iteration: $iteration
                })

                ON CREATE SET
                    c.text = $text,
                    c.type = "iteration_summary",
                    c.raw_entries_json = $raw_entries_json,
                    c.followup_questions = $followups,
                    c.created_at = datetime()

                MERGE (c)-[:BELONGS_TO]->(t)
                """,
                project_id=project_id,
                domain=domain,
                segment=segment,
                topic=topic_norm,
                iteration=iteration,
                chunk_hash=chunk_hash,
                text=chunk_text,
                raw_entries_json=raw_entries_json,
                followups=followups
            )

            created += 1

    return created, iteration


# ================= PIPELINE =================

def run_iteration_excel_pipeline(excel_path, builder, project_id, domain, segment):

    if not Path(excel_path).exists():
        raise FileNotFoundError("❌ Excel file not found")
    print("run_iteration_excel_pipeline called: 300")

    parsed = parse_customer_excel(excel_path)

    print("run_iteration_excel_pipeline called: 304")

    grouped = defaultdict(list)
    for row in parsed:
        grouped[row["topic"]].append(row)

    output = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "topics": {}
    }

    for topic, records in grouped.items():

        answered = [
                f"Q: {r['question']} | A: {r['answer']}"
                for r in records if r["answer"]
            ]

        unanswered = [
                r["question"]
                for r in records if not r["answer"]
            ]


        print(f"\n🧠 Summary for topic: {topic}")

        summary_text = call_summary_llm(topic, answered, unanswered)

        followup_questions = call_followup_llm(
                topic,
                summary_text,
                answered,
                unanswered
            )


        output["topics"][topic] = {
            "llm_summary": summary_text,
            "followup_questions": followup_questions,
            "total_questions": len(records),
            "answered_count": len(answered),
            "unanswered_count": len(unanswered),
            "raw_entries": records
        }

    # Save JSON audit
    output_file = "iteration_summary_generated.json"
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)

    print("\n🧠 Writing iteration into Neo4j...")
    created, iteration = ingest_iteration_chunks(
        builder, project_id, domain, segment, output
    )

    print(f"✅ Stored {created} summaries")
    print(f"🌀 Iteration = {iteration}")

    return output_file
