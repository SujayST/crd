# CRD Backend (Django + Neo4j + Ollama + Chroma)

Backend APIs to ingest CRD documents and customer Excel feedback into Neo4j, generate design clarification questions with Ollama, and manage SME-approved questions in ChromaDB.

## Prerequisites
- Python 3.10+ (matching your venv)
- Running services:
  - Neo4j at `NEO4J_URI` (default `neo4j://localhost:7687`)
  - Ollama at `OLLAMA_URL` with model `OLLAMA_MODEL` (defaults `http://localhost:11434/api/generate`, `openhermes`)
  - ChromaDB at `CHROMA_HOST:CHROMA_PORT` (defaults `localhost:8001`). For local Docker, run `docker-compose` in `crd_chroma_db/`.
- The chunker script `main 1.py` present at repo root (used for CRD doc parsing).

## Setup
```bash
python -m venv venv
source venv/bin/activate
pip install -r crd_backend/requirements.txt
export CHROMA_TELEMETRY_ENABLED=false  # optional: silence telemetry warning
```

Create an `.env` at `crd_backend/.env` (optional; overrides defaults):
```
NEO4J_URI=neo4j://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASS=neo4j
OLLAMA_URL=http://localhost:11434/api/generate
OLLAMA_MODEL=openhermes
CHROMA_HOST=localhost
CHROMA_PORT=8001
DOMAIN_DEFAULT=sp
SEGMENT_DEFAULT=routing
CHUNKER_PATH="main 1.py"
DJANGO_SECRET_KEY=change-me
DJANGO_DEBUG=true
```

Apply Django migrations once:
```bash
cd crd_backend
python manage.py migrate
```

Run the server:
```bash
python manage.py runserver 8000
```

Health check:
```bash
curl http://127.0.0.1:8000/api/health/
```

## API Reference

### 1) POST /api/ingest/crd-docs/
Multipart form-data:
- `project_id` (str, required)
- `project_name` (str, optional; defaults to project_id)
- `domain` (str, optional; default from settings)
- `segment` (str, optional; default from settings)
- `files` (one or many uploaded CRD docs) or `file` (single)

Process: uploads -> chunker (`main 1.py`) -> Neo4j ingest -> question generation.  
Response: ingestion stats + generated questions JSON.

### 2) POST /api/ingest/customer-excel/
Multipart form-data:
- `project_id` (required)
- `domain`, `segment` (optional)
- `file` (Excel workbook)

Process: parse Excel Q&A -> summarize + follow-ups via Ollama -> store iteration summary chunks in Neo4j.  
Response: audit JSON with per-topic summary/follow-ups.

### 3) POST /api/ingest/sme-questions/
JSON body:
```json
{
  "domain": "sp",
  "segment": "routing",
  "topics": {
    "bgp": { "approved_questions": ["..."] }
  }
}
```
Process: pushes SME-approved questions into Chroma question bank (duplicate-safe).  
Response: status dict from `push_sme_questions_to_bank` (added, duplicates, errors).

### 4) GET /api/health/
Simple liveness check.

## Seeding Chroma templates (optional but recommended)
```bash
cd crd_chroma_db
python load_templates.py
```
(Ensure `CHROMA_HOST`/`CHROMA_PORT` env vars match your server.)

## Project layout
- `crd_backend/` Django project and API code.
- `ingest/services/` thin wrappers over existing logic:
  - `graph.py` wraps `MultiProjectGraphBuilder`
  - `chunker.py` shells to `main 1.py`
  - `pipelines.py` orchestrates CRD and Excel ingests
  - `bank.py` pushes SME questions to Chroma
- Root helpers reused: `main_neo_f.py`, `main 1.py`, `crd_question_generator.py`, `iteration_excel_pipeline.py`, `helper.py`.

## Pushing to GitHub (one-time)
```bash
git init
git add .
git commit -m "Add Django CRD backend with ingest APIs"
git branch -M main
git remote add origin git@github.com:<your-username>/<your-repo>.git
git push -u origin main
```

## Common issues
- Chroma telemetry SSL warning: set `CHROMA_TELEMETRY_ENABLED=false`.
- 400 on CRD ingest: ensure you send multipart with `project_id` and at least one `file` or `files[]`.
- Empty Chroma DB: seed templates or add SME questions via `/api/ingest/sme-questions/` or Streamlit app in `crd_chroma_db/streamlit_app.py`.
