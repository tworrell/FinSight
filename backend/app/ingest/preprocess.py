"""Turn messy source documents (PDF / HTML / CSV) into a single normalized markdown-ish
text blob that reads well to an LLM: prose stays prose, tables become markdown tables.

This step exists because zero-shot LLM extraction over raw PDF bytes/text tends to
mangle multi-column financial tables (misaligned columns, merged headers, footnotes
bleeding into numbers). Doing table-aware extraction first, and handing the LLM clean
markdown tables instead of a jumble of whitespace-separated numbers, meaningfully
improves extraction fidelity.
"""

import io

import fitz  # PyMuPDF
import pandas as pd
import pdfplumber
from bs4 import BeautifulSoup


def preprocess_document(filename: str, mime_type: str | None, content: bytes) -> str:
    name = (filename or "").lower()
    mime = mime_type or ""

    if "pdf" in mime or name.endswith(".pdf"):
        return _preprocess_pdf(content)
    if "html" in mime or name.endswith((".html", ".htm", ".eml")):
        return _preprocess_html(content)
    if "csv" in mime or name.endswith(".csv"):
        return _preprocess_csv(content)
    if name.endswith((".xlsx", ".xls")):
        return _preprocess_excel(content)

    # Fallback: treat as plain text.
    return content.decode("utf-8", errors="replace")


def _table_to_markdown(rows: list[list[str | None]]) -> str:
    if not rows or not rows[0]:
        return ""
    cleaned = [[(c or "").strip().replace("\n", " ") for c in row] for row in rows]
    header, *body = cleaned
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(["---"] * len(header)) + " |",
    ]
    for row in body:
        # pad/truncate ragged rows to header width
        row = (row + [""] * len(header))[: len(header)]
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def _preprocess_pdf(content: bytes) -> str:
    parts: list[str] = []

    # Text via PyMuPDF (fast, good reading-order text extraction).
    with fitz.open(stream=content, filetype="pdf") as doc:
        page_texts = [page.get_text("text") for page in doc]

    # Tables via pdfplumber (better structural table detection than raw text).
    page_tables: list[list[list[list[str | None]]]] = []
    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                page_tables.append(page.extract_tables() or [])
    except Exception:
        page_tables = [[] for _ in page_texts]

    for i, text in enumerate(page_texts):
        parts.append(f"## Page {i + 1}\n\n{text.strip()}")
        tables = page_tables[i] if i < len(page_tables) else []
        for t_idx, table in enumerate(tables):
            md = _table_to_markdown(table)
            if md:
                parts.append(f"### Page {i + 1} — Table {t_idx + 1}\n\n{md}")

    return "\n\n".join(parts)


def _preprocess_html(content: bytes) -> str:
    soup = BeautifulSoup(content, "html.parser")

    # Convert any HTML tables to markdown explicitly (pandas is much better at this
    # than asking an LLM to parse nested <tr>/<td> soup).
    md_tables = []
    for table in soup.find_all("table"):
        try:
            dfs = pd.read_html(io.StringIO(str(table)))
            for df in dfs:
                md_tables.append(df.to_markdown(index=False))
        except ValueError:
            pass
        table.decompose()  # remove so it isn't duplicated in the plain-text pass

    text = soup.get_text("\n", strip=True)
    parts = [text]
    for idx, md in enumerate(md_tables):
        parts.append(f"### Table {idx + 1}\n\n{md}")
    return "\n\n".join(parts)


def _preprocess_csv(content: bytes) -> str:
    # Real-world exports often have a handful of metadata rows ("Manager,X") above the
    # actual tabular block, which breaks a naive fixed-width read_csv. Try increasingly
    # tolerant strategies before giving up and handing the LLM the raw text verbatim —
    # Gemini can still parse a simple CSV directly, just less reliably than a clean table.
    try:
        df = pd.read_csv(io.BytesIO(content))
        return f"### CSV data\n\n{df.to_markdown(index=False)}"
    except pd.errors.ParserError:
        pass

    text = content.decode("utf-8", errors="replace")
    lines = text.splitlines()
    field_counts = [line.count(",") for line in lines]
    if field_counts:
        # the header row of the "real" table is usually the first line whose field count
        # is shared by a run of subsequent lines (the data rows).
        mode_count = max(set(field_counts), key=field_counts.count)
        header_idx = next((i for i, c in enumerate(field_counts) if c == mode_count), 0)
        try:
            df = pd.read_csv(io.StringIO("\n".join(lines[header_idx:])))
            preamble = "\n".join(lines[:header_idx])
            table_md = df.to_markdown(index=False)
            return f"### Metadata\n\n{preamble}\n\n### CSV data\n\n{table_md}"
        except pd.errors.ParserError:
            pass

    return f"### CSV data (raw, could not auto-parse as a table)\n\n{text}"


def _preprocess_excel(content: bytes) -> str:
    sheets = pd.read_excel(io.BytesIO(content), sheet_name=None)
    parts = []
    for name, df in sheets.items():
        parts.append(f"### Sheet: {name}\n\n{df.to_markdown(index=False)}")
    return "\n\n".join(parts)
