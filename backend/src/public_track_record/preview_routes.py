"""An optional original fixture preview, with no anonymous database/owner proxy."""

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, Response
from pydantic import ValidationError

from src.performance.identity import digest
from src.public_track_record.snapshot import SnapshotEnvelope

PREVIEW_FILE = Path(__file__).resolve().parents[2] / "demo" / "public_preview_v1.json"
router = APIRouter(prefix="/api/public-preview", tags=["public-demo-preview"])


@router.get("/original", response_model=SnapshotEnvelope)
def original_preview(response: Response) -> SnapshotEnvelope:
    response.headers["Cache-Control"] = "no-store"
    if os.environ.get("ENABLE_DEMO_PREVIEW") != "1":
        raise HTTPException(404, "Local preview is not enabled")
    try:
        result = SnapshotEnvelope.model_validate_json(PREVIEW_FILE.read_bytes())
        if result.status != "local_preview" or result.published_at is not None:
            raise ValueError("Invalid local preview lifecycle")
        if digest(result.snapshot.model_dump(mode="json")) != result.content_sha256:
            raise ValueError("Invalid local preview content identity")
    except (OSError, ValidationError, ValueError) as exc:
        raise HTTPException(503, "Original demo preview is unavailable") from exc
    return result


@router.get("/original/download")
def original_download(response: Response) -> Response:
    result = original_preview(response)
    return Response(
        result.model_dump_json(indent=2),
        media_type="application/json",
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": (
                'attachment; filename="synthetic-demo-public-preview-original-v1.json"'
            ),
            "X-Content-Type-Options": "nosniff",
        },
    )
