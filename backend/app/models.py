import enum
import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config import settings
from app.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class DocumentStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    done = "done"
    error = "error"


class Fund(Base):
    __tablename__ = "funds"
    __table_args__ = (UniqueConstraint("name", name="uq_funds_name"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String, nullable=False)
    manager: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    extractions: Mapped[list["Extraction"]] = relationship(back_populates="fund")
    performance_records: Mapped[list["PerformanceRecord"]] = relationship(back_populates="fund")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    drive_file_id: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String, nullable=True)
    source: Mapped[str] = mapped_column(String, default="upload")  # "drive" | "upload"
    drive_modified_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="document_status"), default=DocumentStatus.pending
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    extractions: Mapped[list["Extraction"]] = relationship(back_populates="document", cascade="all, delete-orphan")
    chunks: Mapped[list["Chunk"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class Extraction(Base):
    __tablename__ = "extractions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    fund_id: Mapped[str | None] = mapped_column(ForeignKey("funds.id"), nullable=True)
    document_type: Mapped[str | None] = mapped_column(String, nullable=True)
    as_of_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    period_start: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    period_end: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    raw_json: Mapped[dict] = mapped_column(JSON, default=dict)
    commentary_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    low_confidence_fields: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    document: Mapped["Document"] = relationship(back_populates="extractions")
    fund: Mapped["Fund | None"] = relationship(back_populates="extractions")
    performance_records: Mapped[list["PerformanceRecord"]] = relationship(
        back_populates="extraction", cascade="all, delete-orphan"
    )


class PerformanceRecord(Base):
    __tablename__ = "performance_records"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    extraction_id: Mapped[str] = mapped_column(ForeignKey("extractions.id", ondelete="CASCADE"))
    fund_id: Mapped[str] = mapped_column(ForeignKey("funds.id"))
    period_month: Mapped[datetime] = mapped_column(Date, nullable=False)
    return_pct: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    nav: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    ytd_return_pct: Mapped[float | None] = mapped_column(Numeric, nullable=True)

    extraction: Mapped["Extraction"] = relationship(back_populates="performance_records")
    fund: Mapped["Fund"] = relationship(back_populates="performance_records")


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    extraction_id: Mapped[str | None] = mapped_column(ForeignKey("extractions.id", ondelete="CASCADE"), nullable=True)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(settings.embedding_dim))

    document: Mapped["Document"] = relationship(back_populates="chunks")


class DriveState(Base):
    """Singleton row tracking Drive OAuth token + folder + sync cursor for this single-tenant demo."""

    __tablename__ = "drive_state"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: "singleton")
    folder_id: Mapped[str | None] = mapped_column(String, nullable=True)
    folder_name: Mapped[str | None] = mapped_column(String, nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sync_cursor: Mapped[str | None] = mapped_column(String, nullable=True)  # ISO modifiedTime watermark
