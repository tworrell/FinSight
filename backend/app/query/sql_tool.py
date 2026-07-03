import re
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session

_FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|grant|revoke|truncate|attach|copy|vacuum|call|do)\b",
    re.IGNORECASE,
)
_SELECT_START = re.compile(r"^\s*(with\b.*?\bselect\b|select)\b", re.IGNORECASE | re.DOTALL)
_LIMIT_PRESENT = re.compile(r"\blimit\s+\d+\b", re.IGNORECASE)

MAX_ROWS = 200


class SQLGuardError(ValueError):
    pass


def _jsonable(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def run_sql(db: Session, query: str, max_rows: int = 50) -> list[dict]:
    """Executes a whitelisted, read-only SELECT against the fund performance schema.

    This is deliberately a lightweight guard (single-statement, SELECT-only, no DDL/DML
    keywords, forced LIMIT) rather than a full SQL parser — sufficient for a demo where the
    caller is our own LLM, not untrusted end users. A production version would additionally
    run this against a Postgres role granted SELECT-only on these four tables.
    """
    stripped = query.strip()
    if stripped.endswith(";"):
        stripped = stripped[:-1]
    if ";" in stripped:
        raise SQLGuardError("Only a single SELECT statement is allowed (no statement stacking).")
    if not _SELECT_START.match(stripped):
        raise SQLGuardError("Only SELECT (or WITH ... SELECT) queries are allowed.")
    if _FORBIDDEN.search(stripped):
        raise SQLGuardError("Query contains a disallowed keyword.")

    max_rows = min(max_rows, MAX_ROWS)
    if not _LIMIT_PRESENT.search(stripped):
        stripped = f"{stripped} LIMIT {max_rows}"

    result = db.execute(text(stripped))
    columns = list(result.keys())
    return [{col: _jsonable(val) for col, val in zip(columns, row)} for row in result.fetchall()]
