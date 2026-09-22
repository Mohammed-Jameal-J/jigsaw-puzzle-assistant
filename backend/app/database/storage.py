"""
File-based storage — JSON only, no database, per MVP constraints.

Layout on disk:

    uploads/
      puzzles/
        {puzzle_id}/
          original.jpg            <- the uploaded photo
          record.json             <- PuzzleRecord serialized
          pieces/
            P0001.png ...         <- extracted piece crops (Phase 2+)
          debug/
            mask.png, contours.png, edges.png   <- Phase 2/4/5 debug overlays

Every puzzle gets its own directory so the whole thing stays inspectable
with `ls` / `cat` — intentional for a 4-5 day MVP with no DB.
"""
from __future__ import annotations

import json
import shutil
import threading
import uuid
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.core.logging import logger
from app.models.puzzle import PuzzleRecord

# One lock per process is fine for a single-container monolith with
# file-based storage; avoids concurrent read/write corruption of record.json.
_lock = threading.Lock()


def new_puzzle_id() -> str:
    return uuid.uuid4().hex[:12]


def puzzle_dir(puzzle_id: str) -> Path:
    return settings.PUZZLES_DIR / puzzle_id


def pieces_dir(puzzle_id: str) -> Path:
    return puzzle_dir(puzzle_id) / "pieces"


def debug_dir(puzzle_id: str) -> Path:
    return puzzle_dir(puzzle_id) / "debug"


def record_path(puzzle_id: str) -> Path:
    return puzzle_dir(puzzle_id) / "record.json"


def create_puzzle_dirs(puzzle_id: str) -> None:
    puzzle_dir(puzzle_id).mkdir(parents=True, exist_ok=True)
    pieces_dir(puzzle_id).mkdir(parents=True, exist_ok=True)
    debug_dir(puzzle_id).mkdir(parents=True, exist_ok=True)


def save_record(record: PuzzleRecord) -> None:
    record.touch()
    path = record_path(record.puzzle_id)
    with _lock:
        tmp_path = path.with_suffix(".json.tmp")
        tmp_path.write_text(json.dumps(record.to_dict(), indent=2))
        tmp_path.replace(path)  # atomic-ish swap, avoids partial writes


def load_record(puzzle_id: str) -> Optional[PuzzleRecord]:
    path = record_path(puzzle_id)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        return PuzzleRecord.from_dict(data)
    except (json.JSONDecodeError, TypeError) as exc:
        logger.error(f"Corrupt record.json for puzzle {puzzle_id}: {exc}")
        return None


def puzzle_exists(puzzle_id: str) -> bool:
    return record_path(puzzle_id).exists()


def delete_puzzle(puzzle_id: str) -> bool:
    d = puzzle_dir(puzzle_id)
    if d.exists():
        shutil.rmtree(d)
        return True
    return False
