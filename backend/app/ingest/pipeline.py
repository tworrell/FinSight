import logging
from datetime import date, datetime

from dateutil import parser as dateparser
from sqlalchemy.orm import Session

from app.ingest.embeddings import chunk_text, embed_documents
from app.ingest.extract import extract_structured_data
from app.ingest.preprocess import preprocess_document
from app.models import Chunk, Document, DocumentStatus, Extraction, Fund, PerformanceRecord
from app.schemas import ExtractionResult

logger = logging.getLogger(__name__)


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return dateparser.parse(value).date()
    except (ValueError, OverflowError):
        return None


def _parse_month(value: str) -> date | None:
    """month strings come back as 'YYYY-MM' (sometimes just 'YYYY-MM-DD')."""
    try:
        parsed = dateparser.parse(value, default=datetime(2000, 1, 1))
        return date(parsed.year, parsed.month, 1)
    except (ValueError, OverflowError):
        return None


def _get_or_create_fund(db: Session, name: str, manager: str | None) -> Fund:
    fund = db.query(Fund).filter(Fund.name == name).one_or_none()
    if fund is None:
        fund = Fund(name=name, manager=manager)
        db.add(fund)
        db.flush()
    elif manager and not fund.manager:
        fund.manager = manager
    return fund


def _persist_extraction(db: Session, document: Document, result: ExtractionResult) -> Extraction:
    fund = _get_or_create_fund(db, result.fund_name, result.manager)

    extraction = Extraction(
        document_id=document.id,
        fund_id=fund.id,
        document_type=result.document_type,
        as_of_date=_parse_date(result.as_of_date),
        period_start=_parse_date(result.period_start),
        period_end=_parse_date(result.period_end),
        raw_json=result.model_dump(),
        commentary_text=result.strategy_commentary,
        low_confidence_fields=result.low_confidence_fields,
    )
    db.add(extraction)
    db.flush()

    for mr in result.monthly_returns:
        period_month = _parse_month(mr.month)
        if period_month is None:
            continue
        db.add(
            PerformanceRecord(
                extraction_id=extraction.id,
                fund_id=fund.id,
                period_month=period_month,
                return_pct=mr.return_pct,
                nav=mr.nav,
                ytd_return_pct=result.ytd_return_pct,
            )
        )

    return extraction


def _persist_chunks(db: Session, document: Document, extraction: Extraction, raw_text: str) -> None:
    pieces = chunk_text(raw_text)
    if not pieces:
        return
    vectors = embed_documents(pieces)
    for text, vector in zip(pieces, vectors):
        db.add(Chunk(document_id=document.id, extraction_id=extraction.id, chunk_text=text, embedding=vector))


def ingest_document(
    db: Session,
    *,
    filename: str,
    mime_type: str | None,
    content: bytes,
    drive_file_id: str | None = None,
    drive_modified_time: datetime | None = None,
    source: str = "upload",
) -> Document:
    """Runs the full pipeline synchronously: preprocess -> LLM extract -> persist -> embed.

    Synchronous/in-request processing is a deliberate scope cut for this project — at real
    volume this would move to a background task queue, but for a "drop ~20 files, hit sync"
    demo it keeps the system trivially easy to reason about and debug.
    """
    document = db.query(Document).filter(Document.drive_file_id == drive_file_id).one_or_none() if drive_file_id else None
    if document is None:
        document = Document(
            filename=filename,
            mime_type=mime_type,
            drive_file_id=drive_file_id,
            drive_modified_time=drive_modified_time,
            source=source,
            status=DocumentStatus.pending,
        )
        db.add(document)
        db.flush()

    document.status = DocumentStatus.processing
    document.error_message = None
    db.commit()

    try:
        raw_text = preprocess_document(filename, mime_type, content)
        document.raw_text = raw_text
        result = extract_structured_data(raw_text)
        extraction = _persist_extraction(db, document, result)
        _persist_chunks(db, document, extraction, raw_text)

        document.status = DocumentStatus.done
        document.processed_at = datetime.utcnow()
        db.commit()
    except Exception as exc:  # noqa: BLE001 - surface any failure per-document without killing a batch sync
        logger.exception("Failed to ingest document %s", filename)
        db.rollback()
        document.status = DocumentStatus.error
        document.error_message = str(exc)[:2000]
        db.commit()

    return document
