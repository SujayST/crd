# ===============================
# helper.py
# Production-ready shared helper
# ===============================

import re
import uuid
import os
import chromadb
from chromadb.config import Settings

# ===============================
# CHROMA DOCKER SERVER CONFIG
# ===============================

CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", 8001))

client = chromadb.HttpClient(
    host=CHROMA_HOST,
    port=CHROMA_PORT,
    settings=Settings(allow_reset=True)
)

template_collection = client.get_or_create_collection("crd_templates")
question_collection = client.get_or_create_collection("crd_questions")

# Connection test (important)
try:
    client.heartbeat()
    print("✅ Connected to ChromaDB server")
except Exception as e:
    print("❌ Cannot connect to ChromaDB:", e)

# ===============================
# EMBEDDING MODEL (LAZY LOAD)
# ===============================

_model = None

def embed_text(text: str):
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        print("🔄 Loading embedding model (first time only)...")
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model.encode(text).tolist()

# ===============================
# TEMPLATE STORE
# ===============================

def add_template(topic, template_text, domain, segment):

    emb = embed_text(template_text)

    template_collection.add(
        ids=[str(uuid.uuid4())],
        documents=[template_text],
        embeddings=[emb],
        metadatas=[{
            "domain": domain,
            "segment": segment,
            "topic": topic.lower(),
            "type": "template",
            "created_at": str(uuid.uuid1())
        }]
    )


def get_templates(topic, domain, segment, limit=20):

    results = template_collection.query(
        query_texts=[topic],
        n_results=limit,
        where={
            "$and": [
                {"domain": domain},
                {"segment": segment},
                {"topic": topic.lower()}
            ]
        }
    )

    if not results["documents"]:
        return []

    return results["documents"][0]

# ===============================
# QUESTION STORE
# ===============================

SIMILARITY_THRESHOLD = 0.90   # stricter for telecom

def check_similarity(question_text, domain, segment, topic):

    emb = embed_text(question_text)

    results = question_collection.query(
        query_embeddings=[emb],
        n_results=5,
        where={
            "$and": [
                {"domain": domain},
                {"segment": segment},
                {"topic": topic.lower()}
            ]
        }
    )

    if not results["documents"]:
        return None

    for i, existing in enumerate(results["documents"][0]):
        distance = results["distances"][0][i]
        similarity = 1 - distance

        if similarity > SIMILARITY_THRESHOLD:
            return {
                "similar_question": existing,
                "similarity": similarity
            }

    return None


def add_question(topic, question_text, source, domain, segment):

    conflict = check_similarity(question_text, domain, segment, topic)

    if conflict:
        return {
            "status": "duplicate",
            "match": conflict
        }

    emb = embed_text(question_text)

    question_collection.add(
        ids=[str(uuid.uuid4())],
        documents=[question_text],
        embeddings=[emb],
        metadatas=[{
            "domain": domain,
            "segment": segment,
            "topic": topic.lower(),
            "source": source,
            "created_at": str(uuid.uuid1())
        }]
    )

    return {"status": "stored"}

# ============================================
# SME PUSH FROM FRONTEND → QUESTION BANK
# ============================================

def push_sme_questions_to_bank(review_json: dict):

    if not review_json:
        return {"status": "error", "msg": "Empty JSON"}

    domain = review_json.get("domain")
    segment = review_json.get("segment")
    topics = review_json.get("topics", {})

    if not domain or not segment:
        return {"status": "error", "msg": "domain/segment missing"}

    total_added = 0
    duplicates = 0
    errors = []

    for topic, payload in topics.items():

        approved = payload.get("approved_questions", [])

        if not approved:
            continue

        for q in approved:

            if not q or not q.strip():
                continue

            result = add_question(
                topic=topic,
                question_text=q.strip(),
                source="sme_approved",
                domain=domain,
                segment=segment
            )

            if result["status"] == "duplicate":
                duplicates += 1
            elif result["status"] == "stored":
                total_added += 1
            else:
                errors.append(q)

    return {
        "status": "completed",
        "questions_added": total_added,
        "duplicates_skipped": duplicates,
        "errors": errors
    }

# ===============================
# SUMMARY EXTRACTOR (Neo4j)
# ===============================

MAX_BULLETS_PER_TOPIC = 12
MAX_SENTENCE_LEN = 220

KEYWORDS = [
    "will", "must", "should", "required", "proposed", "design",
    "migration", "instance", "capacity", "supported", "not",
    "separate", "different", "only", "maximum", "minimum",
    "no direct", "not supported", "will not"
]

def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()

def split_sentences(text: str):
    return re.split(r"(?<=[.])\s+", text)

def is_relevant(sentence: str) -> bool:
    s = sentence.lower()
    return any(k in s for k in KEYWORDS)

def build_topic_summary(session, topic_lc: str):

    sentences = []
    seen = set()

    chunks = session.run("""
        MATCH (t:Topic)
        WHERE toLower(t.name) = $topic
        MATCH (t)<-[:BELONGS_TO]-(c:Chunk)
        RETURN c.chunk_id AS cid, c.text AS text
    """, topic=topic_lc)

    for row in chunks:
        text = normalize(row["text"])

        for s in split_sentences(text):
            if is_relevant(s):
                key = s.lower()
                if key not in seen:
                    seen.add(key)
                    sentences.append(s[:MAX_SENTENCE_LEN])

        related = session.run("""
            MATCH (c1:Chunk {chunk_id:$cid})-[:SIMILAR_TO]-(c2:Chunk)
            RETURN DISTINCT c2.text AS text
        """, cid=row["cid"])

        for r in related:
            r_text = normalize(r["text"])
            for s in split_sentences(r_text):
                if is_relevant(s):
                    key = s.lower()
                    if key not in seen:
                        seen.add(key)
                        sentences.append(s[:MAX_SENTENCE_LEN])

        if len(sentences) >= MAX_BULLETS_PER_TOPIC:
            break

    return sentences[:MAX_BULLETS_PER_TOPIC]
