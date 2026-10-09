"""Identify actual backend source, including uncommitted domain dependencies."""

import hashlib
import json
from pathlib import Path


def digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def source_sha256() -> str:
    root = Path(__file__).resolve().parents[2]
    paths = [*sorted((root / "src").rglob("*.py")), root / "main.py"]
    return digest(
        [
            (path.relative_to(root).as_posix(), hashlib.sha256(path.read_bytes()).hexdigest())
            for path in paths
        ]
    )
