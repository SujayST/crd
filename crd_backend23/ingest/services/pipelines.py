"""
Service layer orchestrating CRD doc ingestion and customer Excel ingestion.
Reuses existing repo modules to minimize code drift.
"""
import json
import tempfile
from pathlib import Path
import sys
from django.conf import settings

from .graph import get_builder
from .chunker import run_chunker

# Ensure repo root on path for existing modules
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Import existing helpers from repo root
from question_generator import generate_questions_json  # type: ignore
import iteration_excel_pipeline  # type: ignore


def _ensure_project_access(builder, project_id: str, project_name: str):
    """
    Ensure the synthetic API user owns the project so access checks pass.
    """
    builder.current_user = "api"
    with builder.driver.session() as session:
        session.run(
            """
            MERGE (u:User {username:$user})
            ON CREATE SET u.password_hash = $pwd, u.created_at = datetime()

            MERGE (p:Project {project_id:$pid})
            ON CREATE SET 
                p.project_name = $pname,
                p.created_at = datetime(),
                p.updated_at = datetime(),
                p.current_iteration = 0

            MERGE (u)-[:OWNS]->(p)
            """,
            user="api",
            pwd="",
            pid=project_id,
            pname=project_name,
        )


def ingest_crd_documents(files, project_id: str, domain: str, segment: str, project_name: str):
    """
    Ingest CRD docs: chunk -> Neo4j -> generate questions.
    Returns dict with ingestion stats and generated questions JSON.
    """
    builder = get_builder()
    _ensure_project_access(builder, project_id, project_name=project_name or project_id)
    builder.add_domain_to_project(project_id, domain)
    builder.add_segment_to_domain(project_id, domain, segment)

    with tempfile.TemporaryDirectory() as tmpdir:
        input_paths = []
        for f in files:
            dest = Path(tmpdir) / f.name
            with open(dest, "wb") as out:
                for chunk in f.chunks():
                    out.write(chunk)
            input_paths.append(dest)

        output_json = Path(tmpdir) / "chunks.json"
        run_chunker(input_paths, output_json)

        topics = builder.get_available_topics_from_json(str(output_json))

        result = builder.build_project_graph(
            project_id=project_id,
            json_file_path=str(output_json),
            domain=domain,
            segment=segment,
            selected_topics=topics,
        )
        if not result.get("success"):
            print("pipelines_83")
            raise RuntimeError(result.get("error"))

        with builder.driver.session() as session:
            questions_json = generate_questions_json(
                session=session, domain=domain, segment=segment
            )

    return {
        "ingest_result": result,
        "questions": questions_json,
    }


def ingest_customer_excel(file_obj, project_id: str, domain: str, segment: str):
    """
    Ingest customer Excel: summarize -> follow-ups -> Neo4j iteration chunks.
    Returns audit JSON contents and iteration number.
    """
    builder = get_builder()
    _ensure_project_access(builder, project_id, project_name=project_id)
    builder.add_domain_to_project(project_id, domain)
    builder.add_segment_to_domain(project_id, domain, segment)
    print("pipelines_106")
    print(file_obj)
    with tempfile.TemporaryDirectory() as tmpdir:

        excel_path = Path(tmpdir) / file_obj.name
        with open(excel_path, "wb") as out:
            for chunk in file_obj.chunks():
                out.write(chunk)
        print("pipelines_114")
        output_file = iteration_excel_pipeline.run_iteration_excel_pipeline(
            excel_path=str(excel_path),
            builder=builder,
            project_id=project_id,
            domain=domain,
            segment=segment,
        )

        with open(output_file, "r") as f:
            audit_json = json.load(f)

    return audit_json
