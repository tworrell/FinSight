import time

from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from sqlalchemy.orm import Session

from app.config import settings
from app.query.sql_tool import SQLGuardError, run_sql
from app.query.vector_tool import semantic_search
from app.schemas import QueryResponse, ToolCallTrace

_client = genai.Client(api_key=settings.gemini_api_key)

_SCHEMA_DESCRIPTION = """
Tables available via run_sql. This is a PostgreSQL database — use PostgreSQL syntax and functions only
(e.g. EXTRACT(MONTH FROM some_date), DATE_TRUNC, ILIKE). Do NOT use SQLite/MySQL functions like STRFTIME.

funds(id, name, manager)
documents(id, filename, status, ingested_at)
extractions(id, document_id, fund_id, document_type, as_of_date, period_start, period_end, commentary_text)
performance_records(id, extraction_id, fund_id, period_month, return_pct, nav, ytd_return_pct)

performance_records.period_month is the first day of the month a return applies to (a DATE).
return_pct / ytd_return_pct are plain percentage numbers (3.1 means 3.1%). Join performance_records
and extractions/documents to funds via fund_id; join extractions to documents via document_id.
Always SELECT funds.name (never just fund_id) when a fund is part of the answer — ids are internal and
meaningless to the user.
"""

_SYSTEM_INSTRUCTION = f"""You are an investment analyst assistant answering questions about a set of fund
documents (factsheets, statements, performance reports from different managers) that have already been
ingested and structured into a database.

{_SCHEMA_DESCRIPTION}

Routing rules:
- Use `run_sql` for anything numeric or comparative: best/worst return, ranking funds, filtering by a
  specific month or date range, averages, counts.
- Use `semantic_search` for qualitative questions about strategy, positioning, or manager commentary —
  it searches narrative text, not numbers.
- A question can need both; call them in any order, and you may call a tool more than once.
- Never fabricate a number that didn't come back from `run_sql`.
- Answer in plain, direct language. Name the specific fund(s) and, where useful, the source document(s).
- If the tools genuinely return nothing relevant, say so instead of guessing.
"""

_TOOLS = [
    types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name="run_sql",
                description=(
                    "Run a single read-only SQL SELECT query against the fund performance database. "
                    "Use for numeric/structured questions."
                ),
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "query": types.Schema(
                            type=types.Type.STRING, description="A single read-only SQL SELECT statement."
                        )
                    },
                    required=["query"],
                ),
            ),
            types.FunctionDeclaration(
                name="semantic_search",
                description=(
                    "Semantic search over fund manager commentary/narrative text for qualitative questions "
                    "(strategy, positioning). Not for exact numbers."
                ),
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "query": types.Schema(type=types.Type.STRING, description="Natural language search query"),
                        "k": types.Schema(type=types.Type.INTEGER, description="Number of results, default 5"),
                    },
                    required=["query"],
                ),
            ),
        ]
    )
]

_MAX_TOOL_ROUNDS = 4


def answer_question(db: Session, question: str) -> QueryResponse:
    contents: list[types.Content] = [types.Content(role="user", parts=[types.Part(text=question)])]
    tool_calls: list[ToolCallTrace] = []
    source_documents: set[str] = set()

    for _ in range(_MAX_TOOL_ROUNDS):
        response = None
        last_error: genai_errors.APIError | None = None
        for attempt in range(3):
            try:
                response = _client.models.generate_content(
                    model=settings.generation_model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=_SYSTEM_INSTRUCTION,
                        tools=_TOOLS,
                        temperature=0.0,
                    ),
                )
                break
            except genai_errors.APIError as exc:
                last_error = exc
                if exc.code == 503 and attempt < 2:  # transient overload — brief backoff and retry
                    time.sleep(1.5 * (attempt + 1))
                    continue
                break
        if response is None:
            return QueryResponse(
                answer=f"The language model API call failed ({last_error.code}): {last_error.message}",
                tool_calls=tool_calls,
                source_documents=sorted(source_documents),
            )
        if not response.candidates or not response.candidates[0].content or not response.candidates[0].content.parts:
            reason = response.candidates[0].finish_reason if response.candidates else "no candidates"
            return QueryResponse(
                answer=f"The model returned an empty response (finish_reason={reason}). Please try rephrasing.",
                tool_calls=tool_calls,
                source_documents=sorted(source_documents),
            )

        candidate = response.candidates[0]
        function_calls = [p.function_call for p in candidate.content.parts if p.function_call]

        if not function_calls:
            answer_text = response.text or "I couldn't generate an answer."
            return QueryResponse(answer=answer_text, tool_calls=tool_calls, source_documents=sorted(source_documents))

        contents.append(candidate.content)
        response_parts = []
        for fc in function_calls:
            args = dict(fc.args or {})
            try:
                if fc.name == "run_sql":
                    rows = run_sql(db, args["query"])
                    payload = {"rows": rows}
                elif fc.name == "semantic_search":
                    results = semantic_search(db, args["query"], int(args.get("k", 5)))
                    for r in results:
                        source_documents.add(r["document"])
                    payload = {"results": results}
                else:
                    payload = {"error": f"Unknown tool '{fc.name}'"}
            except SQLGuardError as exc:
                payload = {"error": str(exc)}
            except Exception as exc:  # noqa: BLE001 - report tool failure back to the model, don't crash the request
                payload = {"error": f"Tool execution failed: {exc}"}

            tool_calls.append(ToolCallTrace(tool=fc.name, input=args, result_preview=str(payload)[:800]))
            response_parts.append(types.Part(function_response=types.FunctionResponse(name=fc.name, response=payload)))

        contents.append(types.Content(role="user", parts=response_parts))

    return QueryResponse(
        answer="I wasn't able to fully resolve this question within the tool-call budget.",
        tool_calls=tool_calls,
        source_documents=sorted(source_documents),
    )
