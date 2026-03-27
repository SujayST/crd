import subprocess
import sys
from pathlib import Path
from django.conf import settings

REPO_ROOT = Path(__file__).resolve().parents[3]


def run_chunker(input_files, output_json):
    """
    Calls the existing chunker script (topic_chunker.py) to produce chunk JSON.
    """
    chunker_path = Path(settings.CHUNKER_PATH)
    if not chunker_path.is_absolute():
        chunker_path = REPO_ROOT / chunker_path

    cmd = [
        sys.executable,
        str(chunker_path),
        "--inputs",
        *[str(p) for p in input_files],
        "--output",
        str(output_json),
        "--format",
        "auto",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Chunker failed: {proc.stderr}")
    if not Path(output_json).exists():
        raise RuntimeError("Chunker did not create output JSON")
    return Path(output_json)
