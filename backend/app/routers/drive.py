from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.drive.client import build_drive_service, download_file, list_files_in_folder, list_folders
from app.drive.oauth import exchange_code, get_auth_url, is_connected, load_credentials
from app.ingest.pipeline import ingest_document
from app.models import DriveState
from app.schemas import DriveFolderOut, DriveStatusOut, SyncResult

router = APIRouter(prefix="/drive", tags=["drive"])


def _get_state(db: Session) -> DriveState:
    state = db.get(DriveState, "singleton")
    if state is None:
        state = DriveState(id="singleton")
        db.add(state)
        db.commit()
        db.refresh(state)
    return state


@router.get("/status", response_model=DriveStatusOut)
def status(db: Session = Depends(get_db)):
    state = _get_state(db)
    return DriveStatusOut(
        connected=is_connected(),
        folder_id=state.folder_id,
        folder_name=state.folder_name,
        last_synced_at=state.last_synced_at,
    )


@router.get("/auth-url")
def auth_url():
    if not settings.google_oauth_client_id or not settings.google_oauth_client_secret:
        raise HTTPException(
            400,
            "Google OAuth client credentials are not configured. Set GOOGLE_OAUTH_CLIENT_ID / "
            "GOOGLE_OAUTH_CLIENT_SECRET in .env (see README).",
        )
    return {"url": get_auth_url()}


@router.get("/oauth2callback")
def oauth2callback(code: str | None = None, error: str | None = None):
    if error:
        return RedirectResponse(f"{settings.frontend_origin}?drive_error={error}")
    if not code:
        raise HTTPException(400, "Missing 'code' in OAuth callback.")
    exchange_code(code)
    return RedirectResponse(f"{settings.frontend_origin}?drive_connected=1")


@router.get("/folders", response_model=list[DriveFolderOut])
def folders(q: str | None = None):
    creds = load_credentials()
    if creds is None:
        raise HTTPException(400, "Drive is not connected yet.")
    service = build_drive_service(creds)
    return list_folders(service, query=q)


class SelectFolderIn(BaseModel):
    folder_id: str
    folder_name: str


@router.post("/select-folder", response_model=DriveStatusOut)
def select_folder(payload: SelectFolderIn, db: Session = Depends(get_db)):
    state = _get_state(db)
    state.folder_id = payload.folder_id
    state.folder_name = payload.folder_name
    state.sync_cursor = None
    db.commit()
    return DriveStatusOut(
        connected=is_connected(), folder_id=state.folder_id, folder_name=state.folder_name, last_synced_at=state.last_synced_at
    )


@router.post("/sync", response_model=SyncResult)
def sync(db: Session = Depends(get_db)):
    creds = load_credentials()
    if creds is None:
        raise HTTPException(400, "Drive is not connected yet.")

    state = _get_state(db)
    if not state.folder_id:
        raise HTTPException(400, "No folder selected yet.")

    service = build_drive_service(creds)
    files = list_files_in_folder(service, state.folder_id, modified_after=state.sync_cursor)

    processed, failed = 0, 0
    latest_modified = state.sync_cursor
    for f in files:
        content = download_file(service, f["id"], f["mimeType"])
        doc = ingest_document(
            db,
            filename=f["name"],
            mime_type=f["mimeType"],
            content=content,
            drive_file_id=f["id"],
            drive_modified_time=f["modifiedTime"],
            source="drive",
        )
        if doc.status.value == "done":
            processed += 1
        else:
            failed += 1
        if latest_modified is None or f["modifiedTime"] > latest_modified:
            latest_modified = f["modifiedTime"]

    state.sync_cursor = latest_modified
    state.last_synced_at = datetime.now(timezone.utc)
    db.commit()

    return SyncResult(new_files=len(files), processed=processed, failed=failed, last_synced_at=state.last_synced_at)
