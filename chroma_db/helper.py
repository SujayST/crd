import os
import uuid
import chromadb
from fastembed import TextEmbedding

# ================= CHROMA CONNECT =================

CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", 8001))

client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)

template_collection = client.get_or_create_collection("crd_templates")
question_collection = client.get_or_create_collection("crd_questions")

# ================= FAST EMBEDDINGS =================

embed_model = TextEmbedding()

def embed_text(text: str):
    return list(embed_model.embed([text]))[0].tolist()

# ================= TEMPLATE STORE =================

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
            "type": "template"
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

# ================= QUESTION STORE =================

SIMILARITY_THRESHOLD = 0.85

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
        dist = results["distances"][0][i]
        sim = 1 - dist

        if sim > SIMILARITY_THRESHOLD:
            return {"similar_question": existing, "similarity": sim}

    return None

def add_question(topic, question_text, source, domain, segment):

    conflict = check_similarity(question_text, domain, segment, topic)

    if conflict:
        return {"status": "duplicate", "match": conflict}

    emb = embed_text(question_text)

    question_collection.add(
        ids=[str(uuid.uuid4())],
        documents=[question_text],
        embeddings=[emb],
        metadatas=[{
            "domain": domain,
            "segment": segment,
            "topic": topic.lower(),
            "source": source
        }]
    )

    return {"status": "stored"}

# ================= SME PUSH =================

def push_sme_questions_to_bank(review_json):

    domain = review_json.get("domain")
    segment = review_json.get("segment")
    topics = review_json.get("topics", {})

    added = 0

    for topic, payload in topics.items():
        approved = payload.get("approved_questions", [])

        for q in approved:
            res = add_question(topic, q, "sme", domain, segment)
            if res["status"] == "stored":
                added += 1

    return {"questions_added": added}
