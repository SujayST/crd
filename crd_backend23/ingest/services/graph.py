"""
Wrapper around the existing MultiProjectGraphBuilder (from repo root graph_db_setup.py).
Keeps instantiation centralized and lazy.
"""
from pathlib import Path
import sys
from django.conf import settings

# Ensure repo root (one level above Django project) is on sys.path
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from graph_db_setup import MultiProjectGraphBuilder  # type: ignore

_builder = None


def get_builder():
    global _builder
    if _builder is None:
        _builder = MultiProjectGraphBuilder(
            neo4j_uri=settings.NEO4J_URI,
            neo4j_user=settings.NEO4J_USER,
            neo4j_password=settings.NEO4J_PASS,
        )
        # simple fallback user context
        _builder.current_user = "api"
    return _builder
