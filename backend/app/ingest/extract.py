from google import genai
from google.genai import types

from app.config import settings
from app.schemas import ExtractionResult

_client = genai.Client(api_key=settings.gemini_api_key)

_SYSTEM_INSTRUCTION = """You are a financial-document data extraction engine.

You will be given the preprocessed text (with tables already converted to markdown) of a
single document from an alternative-investment fund manager — a factsheet, account
statement, or performance report. Layouts, terminology, and units vary wildly between
managers; do not assume any fixed template.

Rules:
- Only extract values that are actually present in the text. Never invent numbers.
- Normalize percentages to plain numbers (e.g. "2.3%" -> 2.3, "(1.4%)" -> -1.4).
- Normalize currency shorthand to plain numbers (e.g. "$310mm" / "$310 million" -> 310000000).
- Dates must be ISO format (YYYY-MM-DD). If only a month/year is given for a monthly return,
  use the last day of that month is NOT required — just use YYYY-MM for the `month` field on
  monthly_returns, and full ISO dates elsewhere.
- If a field cannot be determined, leave it null rather than guessing.
- List any field you had to infer from ambiguous formatting in `low_confidence_fields`.
"""


def extract_structured_data(document_text: str) -> ExtractionResult:
    response = _client.models.generate_content(
        model=settings.generation_model,
        contents=document_text[:200_000],  # generous cap; guards against pathological inputs
        config=types.GenerateContentConfig(
            system_instruction=_SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=ExtractionResult,
            temperature=0.0,
        ),
    )
    result = response.parsed
    if result is None:
        raise ValueError(f"Gemini returned no parseable extraction. Raw response: {response.text!r}")
    return result
