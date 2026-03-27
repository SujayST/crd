"""
Thin wrapper around push_sme_questions_to_bank from the root helper.py.
"""
from pathlib import Path
import sys

# Ensure repo root is importable
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from helper import push_sme_questions_to_bank  # type: ignore


def ingest_sme_questions(review_json: dict):
    """
    Delegates to existing helper; returns its result dict.
    """
    return push_sme_questions_to_bank(review_json)
