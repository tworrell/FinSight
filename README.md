# Equi Document Intelligence -Tara Worrell

Connect a Google Drive folder, drop in messy fund factsheets/statements/performance reports (PDF, CSV,
HTML), and get a searchable, queryable table of structured data — automatically re-synced whenever new
files land in the folder.

> Built for the Equi Founding Engineer / Applied AI Lead take-home (Option A).

## What it does

1. **Connect** a Google account via OAuth and pick a Drive folder to watch (or just drag files onto the
   "Manual upload" card — same pipeline, no Drive required).
2. **Sync Now** (or the 30s auto-poll) lists files in that folder via `files.list` with a `modifiedTime`
   filter, downloads anything new/changed, and runs it through the ingest pipeline.
3. Each document is **preprocessed** (tables → clean markdown, regardless of PDF/CSV/HTML) and then handed
   to **Gemini** with a strict structured-output schema — fund name, document type, monthly returns, NAV,
   AUM, benchmark, YTD, and a short strategy commentary blurb — no per-manager template configuration.
4. Structured numbers land in Postgres; a chunked-and-embedded copy of the full document text lands in
   **pgvector** for semantic search.
5. The **documents table** lets you filter by fund/status and expand any row to see the extracted fields
   and the monthly performance breakdown.
6. The **query box** answers natural-language questions using a small Gemini function-calling agent with
   two tools: a guarded read-only **SQL tool** (numeric/ranking questions) and a **vector search tool**
   (qualitative/strategy questions). The model decides which to use — and shows its work.

## Architecture

```
Next.js (TypeScript) ──HTTP──▶ FastAPI (Python)
                                   │
                    ┌──────────────┼───────────────────┐
                    ▼              ▼                    ▼
              Drive OAuth /   Ingest pipeline      Query agent
              files.list      (preprocess →        (Gemini function
                               Gemini extract →      calling: run_sql +
                               persist → embed)       semantic_search)
                    │              │                    │
                    └──────────────┴────────────────────┘
                                   ▼
                     Postgres + pgvector (SQLAlchemy)
```

**Backend**: FastAPI, SQLAlchemy, Postgres + pgvector, PyMuPDF/pdfplumber/BeautifulSoup/pandas for
preprocessing, `google-genai` for Gemini.
**Frontend**: Next.js 16 (App Router) + TypeScript + Tailwind, plain `fetch`-based client components — no
extra state library needed for a dashboard this size.

## Key design decisions

These map to the discovery conversation before building:

- **Preprocess before extracting, don't go zero-shot.** Financial tables are exactly where zero-shot LLM
  extraction falls over (merged headers, footnotes bleeding into numbers). `preprocess.py` uses PyMuPDF for
  reading-order text and `pdfplumber` for table-structure detection, converting tables to clean markdown
  *before* Gemini ever sees them. The same normalization applies to HTML "emails" (`pandas.read_html` on
  any `<table>`) and CSVs (including ones with metadata rows above the real table — a real-world case that
  showed up in the synthetic data and is handled with a fallback header-detection pass).
- **One schema, any layout.** `schemas.ExtractionResult` is a single Pydantic model passed to Gemini as
  `response_schema`. Every document — table-heavy factsheet, narrative-heavy statement, CSV export, HTML
  update — gets coerced into the same shape (fund, period, monthly returns, NAV, AUM, benchmark, YTD,
  commentary), with a `low_confidence_fields` list so the model flags what it wasn't sure about instead of
  silently guessing. No per-manager parser configuration.
- **Pragmatic Drive sync, not webhooks.** Real-time push notifications need a public endpoint + domain
  verification + subscription renewal — a lot of infra for a local demo. Instead: "Sync Now" + a 30-second
  auto-poll while the tab is open, both hitting `files.list` with a `modifiedTime` watermark so repeat
  syncs are cheap and idempotent. Swapping this for a webhook later is additive, not a rewrite.
- **Hybrid querying, not pure RAG.** Pure vector RAG is bad at "which fund had the *best* January return" —
  that's an aggregation, not a similarity match. So extracted numbers go into normalized Postgres tables
  (`funds`, `extractions`, `performance_records`) queryable via a guarded **read-only SQL tool**, while the
  full document text is chunked and embedded into **pgvector** for a **semantic search tool** that handles
  "which funds are pursuing a distressed-credit strategy"-style questions. A Gemini function-calling loop
  (`query/agent.py`) picks one or both tools per question and cites which it used and which source
  documents it drew from.
- **Postgres + pgvector over a separate vector DB.** One database, one ORM (SQLAlchemy), both query
  patterns — no second system to run or reason about for this scale.
- **Gemini over other providers.** Native, well-supported structured-output (`response_schema`) and
  function-calling, plus a first-class embeddings API — one SDK for extraction, embeddings, and the query
  agent.

## Setup

### Prerequisites

- Docker (for Postgres + pgvector)
- Python 3.11+ and Node 20+
- A **Gemini API key** — [aistudio.google.com/apikey](https://aistudio.google.com/apikey)

### 1. Environment

```bash
cp .env.example .env
# edit .env and set GEMINI_API_KEY
```

### 2. Database

```bash
docker compose up -d
```

This starts Postgres with the `pgvector` extension on `localhost:5433` (chosen to avoid clashing with a
default local Postgres on 5432). The backend creates all tables and the `vector` extension automatically on
first startup — no migrations to run.

### 3. Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 4. Frontend

```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:3000`.

### 5. Try it without Drive

Click **"Choose Files"** under "Manual upload" and select a few files from `sample_data/` (or generate a
fresh batch with `python3 scripts/generate_sample_data.py`). They go through the identical pipeline Drive
sync uses, so you can see extraction + querying working before touching OAuth.

### 6. Google Drive setup (only needed to demo the Drive integration itself)

1. In the [Google Cloud Console](https://console.cloud.google.com/), create a project (or use an existing
   one) and enable the **Google Drive API**.
2. Configure the OAuth consent screen (External is fine for testing; add yourself as a test user).
3. Create an **OAuth client ID** of type "Web application" with an authorized redirect URI of
   `http://localhost:8000/drive/oauth2callback`.
4. Copy the client ID/secret into `.env` as `GOOGLE_OAUTH_CLIENT_ID` / `GOOGLE_OAUTH_CLIENT_SECRET`.
5. Restart the backend, click **"Connect Google Drive"**, authorize, pick a folder that contains some fund
   documents, and hit **Sync Now**.

## Running tests

```bash
cd backend
source .venv/bin/activate
pytest
```

Covers the pure, deterministic logic that doesn't require a live DB, Drive account, or Gemini API call:
document preprocessing (`ingest/preprocess.py` — table-to-markdown conversion, the messy-CSV
header-detection fallback, HTML table extraction), the SQL tool's guardrails (`query/sql_tool.py` —
SELECT-only, no statement stacking, forced `LIMIT`), and the date-parsing helpers in the ingest pipeline.
Extraction/embeddings/the query agent/Drive OAuth are exercised via the manual-upload + query flow
end-to-end instead of unit tests — mocking the Gemini/Drive clients meaningfully would cost more than it's
worth at this scope.

## Example questions to try

- "Which fund had the best January return?" → SQL tool
- "Rank all funds by YTD return." → SQL tool
- "Which funds are pursuing a distressed or credit-focused strategy?" → vector search tool
- "How did Blue Harbor do in Q1 and what's driving their positioning?" → both tools

## Known limitations / what's next for production

- **Synchronous ingestion.** Each document is processed inline within the sync/upload request. Fine for a
  "drop ~20 files, hit sync" demo; at real volume this moves to a background task queue (Celery/RQ/Cloud
  Tasks) with per-document retries.
- **Single-tenant.** One Drive connection, one token store, no multi-user auth — intentionally out of scope
  for a take-home; the schema has no user/org boundary yet.
- **SQL tool guardrails are a lightweight blocklist** (SELECT-only, no DDL/DML keywords, single statement,
  forced `LIMIT`), sufficient since the caller is our own LLM, not an untrusted end user. A production
  version would also run it against a Postgres role granted `SELECT`-only on the four relevant tables.
- **Gemini free-tier quotas.** The `gemini-2.5-flash` free tier is capped at 20 requests/day, which is easy
  to hit while iterating — `GENERATION_MODEL` in `.env`/config is swappable (e.g. to
  `gemini-2.5-flash-lite`, which has a separate quota bucket) or point at a billing-enabled project for
  real usage.
- **No dedupe on manual uploads.** Drive sync dedupes by `drive_file_id`; manual uploads always create a
  new document row (uploading the same file twice makes two rows). Fine for a demo path meant for quick
  local testing.

## Repo layout

```
backend/app/
  drive/       Google OAuth + Drive API client
  ingest/      preprocess → extract (Gemini) → embed → persist pipeline
  query/       SQL tool, vector tool, and the function-calling agent that routes between them
  routers/     FastAPI endpoints (drive, documents, query)
  models.py    SQLAlchemy models (funds, documents, extractions, performance_records, chunks)
  schemas.py   Pydantic API + LLM-extraction schemas
frontend/      Next.js dashboard (Drive connect, upload, documents table, query panel)
sample_data/   synthetic, intentionally differently-formatted fund documents for testing
scripts/       generate_sample_data.py
```
