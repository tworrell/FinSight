from app.ingest.preprocess import (
    _preprocess_csv,
    _preprocess_html,
    _table_to_markdown,
    preprocess_document,
)


def test_table_to_markdown_basic():
    rows = [["Month", "Return"], ["Jan-25", "3.1%"], ["Feb-25", "-0.4%"]]
    md = _table_to_markdown(rows)
    assert md.splitlines()[0] == "| Month | Return |"
    assert "| --- | --- |" in md
    assert "| Jan-25 | 3.1% |" in md


def test_table_to_markdown_empty_input():
    assert _table_to_markdown([]) == ""
    assert _table_to_markdown([[]]) == ""


def test_table_to_markdown_pads_ragged_rows():
    rows = [["A", "B", "C"], ["1", "2"], ["x", "y", "z", "extra"]]
    md = _table_to_markdown(rows)
    lines = md.splitlines()
    assert lines[2] == "| 1 | 2 |  |"  # padded to 3 columns
    assert lines[3] == "| x | y | z |"  # truncated to 3 columns


def test_preprocess_csv_clean_table():
    content = b"Month,Return\n2025-01,3.1\n2025-02,-0.4\n"
    out = _preprocess_csv(content)
    assert "### CSV data" in out
    assert "2025-01" in out
    assert "3.1" in out


def test_preprocess_csv_with_metadata_rows_falls_back_gracefully():
    # Mirrors a real export we hit: metadata rows above the real table break a naive
    # read_csv (fewer commas per line than the actual data rows below).
    content = (
        b"Report,Summit Ridge Macro Fund\n"
        b"Manager,Summit Ridge Capital\n"
        b"\n"
        b"Month,Return (%),NAV\n"
        b"2024-11,1.8,156.20\n"
        b"2024-12,2.5,160.10\n"
    )
    out = _preprocess_csv(content)
    assert "### Metadata" in out
    assert "### CSV data" in out
    assert "156.2" in out or "156.20" in out


def test_preprocess_csv_empty_file_falls_back_gracefully():
    # pandas' C parser is very tolerant of malformed CSV text (quote errors, ragged rows,
    # etc.) and rescues almost all of it into a table via the metadata-row fallback — but
    # a genuinely empty file raises EmptyDataError, a different exception that must be
    # caught separately or it escapes the parser entirely.
    out = _preprocess_csv(b"")
    assert "raw" in out.lower()


def test_preprocess_html_extracts_table_and_text():
    html = b"""
    <html><body>
    <p>Fund commentary goes here.</p>
    <table><tr><th>Metric</th><th>Value</th></tr><tr><td>NAV</td><td>98.42</td></tr></table>
    </body></html>
    """
    out = _preprocess_html(html)
    assert "Fund commentary goes here." in out
    assert "### Table 1" in out
    assert "98.42" in out


def test_preprocess_document_dispatches_by_extension():
    csv_out = preprocess_document("report.csv", None, b"A,B\n1,2\n")
    assert "CSV data" in csv_out

    html_out = preprocess_document("update.html", None, b"<p>hello</p>")
    assert "hello" in html_out

    text_out = preprocess_document("notes.txt", None, b"plain text content")
    assert text_out == "plain text content"


def test_preprocess_document_dispatches_by_mime_type_when_extension_ambiguous():
    # Drive-downloaded files can have a generic/missing extension; mime type should win.
    out = preprocess_document("export", "text/csv", b"A,B\n1,2\n")
    assert "CSV data" in out
