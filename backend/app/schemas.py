from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# LLM extraction schema — this is what we hand Gemini as `response_schema`.
# Every document, regardless of source layout, is coerced into this shape.
# ---------------------------------------------------------------------------


class MonthlyReturn(BaseModel):
    month: str = Field(description="Calendar month this return applies to, formatted YYYY-MM")
    return_pct: float | None = Field(default=None, description="Net return for the month, as a percentage, e.g. 2.3 for 2.3%")
    nav: float | None = Field(default=None, description="Net asset value / unit price at month end, if stated")


class ExtractionResult(BaseModel):
    fund_name: str = Field(description="Name of the fund or investment vehicle this document is about")
    manager: str | None = Field(default=None, description="Fund manager / GP / issuing firm name, if stated")
    document_type: Literal["factsheet", "statement", "performance_report", "other"] = Field(
        description="Best guess at what kind of document this is"
    )
    as_of_date: str | None = Field(default=None, description="The reporting 'as of' date, ISO format YYYY-MM-DD")
    period_start: str | None = Field(default=None, description="Start of the reporting period covered, ISO YYYY-MM-DD")
    period_end: str | None = Field(default=None, description="End of the reporting period covered, ISO YYYY-MM-DD")
    monthly_returns: list[MonthlyReturn] = Field(
        default_factory=list, description="Any monthly (or period) returns found in tables in the document"
    )
    ytd_return_pct: float | None = Field(default=None, description="Year-to-date return percentage, if stated")
    since_inception_return_pct: float | None = Field(default=None, description="Since-inception / ITD return percentage")
    nav: float | None = Field(default=None, description="Most recent NAV / unit price stated in the document")
    aum: float | None = Field(default=None, description="Assets under management, in the currency stated, as a plain number")
    benchmark_name: str | None = Field(default=None, description="Name of the benchmark index compared against, if any")
    benchmark_return_pct: float | None = Field(default=None, description="The benchmark's return over the same period, if stated")
    strategy_commentary: str | None = Field(
        default=None,
        description="A concise summary (2-5 sentences) of the fund's strategy, positioning, or manager commentary "
        "narrative found in the document — used for qualitative search, not numeric analysis",
    )
    low_confidence_fields: list[str] = Field(
        default_factory=list,
        description="Names of fields above you were not confident about (ambiguous layout, unclear units, etc.)",
    )


# ---------------------------------------------------------------------------
# API schemas
# ---------------------------------------------------------------------------


class FundOut(BaseModel):
    id: str
    name: str
    manager: str | None
    model_config = {"from_attributes": True}


class PerformanceRecordOut(BaseModel):
    period_month: date
    return_pct: float | None
    nav: float | None
    ytd_return_pct: float | None
    model_config = {"from_attributes": True}


class ExtractionOut(BaseModel):
    id: str
    document_type: str | None
    as_of_date: date | None
    period_start: date | None
    period_end: date | None
    raw_json: dict
    commentary_text: str | None
    low_confidence_fields: list[str]
    fund: FundOut | None
    performance_records: list[PerformanceRecordOut] = []
    model_config = {"from_attributes": True}


class DocumentOut(BaseModel):
    id: str
    filename: str
    mime_type: str | None
    source: str
    status: str
    error_message: str | None
    ingested_at: datetime
    processed_at: datetime | None
    extractions: list[ExtractionOut] = []
    model_config = {"from_attributes": True}


class DriveStatusOut(BaseModel):
    connected: bool
    folder_id: str | None = None
    folder_name: str | None = None
    last_synced_at: datetime | None = None


class DriveFolderOut(BaseModel):
    id: str
    name: str


class SyncResult(BaseModel):
    new_files: int
    processed: int
    failed: int
    last_synced_at: datetime


class QueryRequest(BaseModel):
    question: str


class ToolCallTrace(BaseModel):
    tool: str
    input: dict
    result_preview: str


class QueryResponse(BaseModel):
    answer: str
    tool_calls: list[ToolCallTrace]
    source_documents: list[str] = []
