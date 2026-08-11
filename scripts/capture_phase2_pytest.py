from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "tests" / ".phase2-pytest-diagnostic.txt"

result = subprocess.run(
    ["python", "-m", "pytest", "-q"],
    cwd=ROOT,
    text=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    check=False,
)
OUTPUT.write_text(result.stdout, encoding="utf-8")
raise SystemExit(result.returncode)
