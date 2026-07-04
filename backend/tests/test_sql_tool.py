from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.query.sql_tool import SQLGuardError, run_sql


def _mock_db(columns, rows):
    """A fake Session whose .execute() returns a result with the given columns/rows,
    so we can test run_sql's own logic without a real database connection."""
    result = MagicMock()
    result.keys.return_value = columns
    result.fetchall.return_value = rows
    db = MagicMock()
    db.execute.return_value = result
    return db


@pytest.mark.parametrize(
    "bad_query",
    [
        "UPDATE funds SET name = 'x'",
        "DELETE FROM funds",
        "DROP TABLE funds",
        "INSERT INTO funds (name) VALUES ('x')",
        "SELECT * FROM funds; DROP TABLE funds;",  # statement stacking
        "not sql at all",
    ],
)
def test_run_sql_rejects_disallowed_queries(bad_query):
    with pytest.raises(SQLGuardError):
        run_sql(db=None, query=bad_query)  # guard fails before db is ever touched


def test_run_sql_allows_plain_select():
    db = _mock_db(["name"], [("Acme Distressed Opportunities Fund LP",)])
    rows = run_sql(db, "SELECT name FROM funds")
    assert rows == [{"name": "Acme Distressed Opportunities Fund LP"}]


def test_run_sql_allows_with_cte_select():
    db = _mock_db(["name"], [("Acme",)])
    rows = run_sql(db, "WITH ranked AS (SELECT name FROM funds) SELECT name FROM ranked")
    assert rows == [{"name": "Acme"}]


def test_run_sql_injects_limit_when_missing():
    db = _mock_db(["name"], [])
    run_sql(db, "SELECT name FROM funds", max_rows=25)
    executed_sql = str(db.execute.call_args[0][0])
    assert "LIMIT 25" in executed_sql


def test_run_sql_does_not_double_inject_limit():
    db = _mock_db(["name"], [])
    run_sql(db, "SELECT name FROM funds LIMIT 5")
    executed_sql = str(db.execute.call_args[0][0])
    assert executed_sql.count("LIMIT") == 1


def test_run_sql_caps_max_rows_at_ceiling():
    db = _mock_db(["name"], [])
    run_sql(db, "SELECT name FROM funds", max_rows=10_000)
    executed_sql = str(db.execute.call_args[0][0])
    assert "LIMIT 200" in executed_sql  # MAX_ROWS ceiling, not the requested 10,000


def test_run_sql_converts_decimal_and_date_to_jsonable_types():
    db = _mock_db(["return_pct", "period_month"], [(Decimal("3.1"), date(2025, 1, 31))])
    rows = run_sql(db, "SELECT return_pct, period_month FROM performance_records")
    assert rows == [{"return_pct": 3.1, "period_month": "2025-01-31"}]
    assert isinstance(rows[0]["return_pct"], float)
