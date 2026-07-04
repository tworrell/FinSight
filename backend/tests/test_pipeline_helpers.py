from datetime import date

from app.ingest.pipeline import _parse_date, _parse_month


def test_parse_date_valid_iso():
    assert _parse_date("2025-01-31") == date(2025, 1, 31)


def test_parse_date_none_input():
    assert _parse_date(None) is None
    assert _parse_date("") is None


def test_parse_date_garbage_input_returns_none():
    assert _parse_date("not a date") is None


def test_parse_month_year_month_only():
    assert _parse_month("2025-01") == date(2025, 1, 1)


def test_parse_month_ignores_day_forces_first_of_month():
    # monthly_returns.month is documented as YYYY-MM, but Gemini occasionally includes a
    # day — we deliberately normalize to the 1st regardless, so records for the same month
    # always dedupe/sort consistently.
    assert _parse_month("2025-01-15") == date(2025, 1, 1)


def test_parse_month_garbage_input_returns_none():
    assert _parse_month("not a month") is None
