from datetime import date

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session, joinedload

from app.db import get_db
from app.ingest.pipeline import ingest_document
from app.models import Document, Extraction, Fund
from app.schemas import DocumentOut, FundOut

router = APIRouter(tags=["documents"])


@router.get("/funds", response_model=list[FundOut])
def list_funds(db: Session = Depends(get_db)):
    return db.query(Fund).order_by(Fund.name).all()


@router.get("/documents", response_model=list[DocumentOut])
def list_documents(
    fund_id: str | None = None,
    status: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Document).options(
        joinedload(Document.extractions).joinedload(Extraction.fund),
        joinedload(Document.extractions).joinedload(Extraction.performance_records),
    )
    if status:
        query = query.filter(Document.status == status)
    if fund_id or date_from or date_to:
        query = query.join(Document.extractions)
        if fund_id:
            query = query.filter(Extraction.fund_id == fund_id)
        if date_from:
            query = query.filter(Extraction.as_of_date >= date_from)
        if date_to:
            query = query.filter(Extraction.as_of_date <= date_to)
    return query.order_by(Document.ingested_at.desc()).distinct().all()


@router.get("/documents/{document_id}", response_model=DocumentOut)
def get_document(document_id: str, db: Session = Depends(get_db)):
    doc = (
        db.query(Document)
        .options(
            joinedload(Document.extractions).joinedload(Extraction.fund),
            joinedload(Document.extractions).joinedload(Extraction.performance_records),
        )
        .filter(Document.id == document_id)
        .one_or_none()
    )
    if doc is None:
        raise HTTPException(404, "Document not found")
    return doc


@router.post("/documents/upload", response_model=list[DocumentOut])
async def upload_documents(files: list[UploadFile], db: Session = Depends(get_db)):
    """Manual-upload path — lets you exercise the same ingest pipeline as Drive sync without
    needing a live Drive connection (useful for local testing/demoing)."""
    results = []
    for f in files:
        content = await f.read()
        doc = ingest_document(db, filename=f.filename, mime_type=f.content_type, content=content, source="upload")
        results.append(doc)
    return results
