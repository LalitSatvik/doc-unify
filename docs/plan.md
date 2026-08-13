# Unified Document-to-Data Platform

## Context

The user repeatedly had to manually pull data out of hundreds of investor
reports (PDFs, mixed layouts, lots of noise alongside the actual numbers)
and unify it into one consistent table — a slow, repetitive, and
error-prone process. The hard part isn't reading a single PDF; it's
figuring out **which fields are even extractable across a heterogeneous
corpus**, and **reconciling the fact that "Revenue" in one report and
"Net Sales" in another may or may not be the same measurement**, reported
in different units and sometimes different methodologies.

This project builds a general platform: feed it arbitrary documents
(PDF/image/docx/pptx today, video later), and it (a) figures out what
structured data can be pulled out, (b) proposes a single unified schema
across the whole corpus — catching when two differently-labeled fields
are really the same thing, and flagging when they only look the same —
and (c) lets the user drive extraction conversationally via a chat agent.
It's built with free/local tools (Ollama, open embedding models, Postgres)
so it's fully open-source, runnable offline, and portfolio-ready on
GitHub, with an optional hosted demo using a free-tier cloud LLM as a
swappable backend.

Video ingestion is explicitly deferred — the ingestion interface is
designed to support it later without rework, but no video pipeline is
built in this plan.

## Recommended Approach

Hybrid **embedding-clustering + LLM cluster review** for schema discovery
(over LLM-only clustering, which doesn't scale past a handful of docs, and
pure user-seeded extraction, which skips the actual hard problem):

1. Extract *candidate fields* per document with the LLM: label as written,
   value, unit as written, a short definition/context sentence, and a
   source citation (doc + page + snippet).
2. Embed each candidate's label+context and cluster embeddings across the
   whole corpus (cheap, scales to hundreds of docs) to group likely-
   equivalent fields (e.g. "Total Revenue," "Net Sales," "Top-line").
3. LLM reviews each cluster (not every pairwise candidate) to propose a
   canonical field name + definition, and explicitly flags clusters that
   look like they conflate two different measurement methodologies (e.g.
   GAAP vs non-GAAP) instead of silently merging them.
4. User approves/edits the proposed unified schema (rename, merge, split,
   reject) via the UI or the chat agent. A user can also seed known target
   fields up front; discovery just fills in / proposes the rest around
   them — the two modes share the same extraction/normalization backend.

Once a schema is approved, every document is (re-)extracted against it
with retrieval-augmented structured-output prompting. Every cell stores
raw value + raw unit/methodology + normalized value + confidence + source
citation. Cells that aren't mechanically normalizable (ambiguous units,
differing methodology) are flagged into a human review queue rather than
silently coerced.

## Architecture

```
/backend  (Python, FastAPI)
  app/
    ingestion/    per-format extractors → common ContentBlock interface
                   (text, table, image-region; page/location + bbox)
                   v1: pdf.py, image.py, docx.py, pptx.py
                   (video.py left as a documented stub against the same interface)
    embedding/     chunking + vector store (pgvector) for retrieval
    schema/        candidate extraction, clustering, LLM cluster review,
                   schema registry CRUD, approval workflow
    extraction/    structured extraction against an approved schema,
                   normalization (unit/scale conversion), confidence
                   scoring, review-queue logic
    agent/         tool-calling chat agent + tool definitions (propose
                   schema, run extraction, query table, explain cell
                   provenance, export)
    llm/           LLMProvider interface + OllamaProvider (local) and
                   CloudProvider (free-tier, for hosted demo) — everything
                   above talks to this interface, never to a specific model
    db/            SQLAlchemy models + migrations (documents, content
                   blocks, schema_fields, table_cells, review_queue)
    api/           FastAPI routers exposing the above to the frontend
  tests/

/frontend (Next.js/React)
  components: upload, chat panel, schema review table, unified data grid
  (with per-cell provenance popovers), export controls

docker-compose.yml   postgres(+pgvector), ollama, backend, frontend
README.md            what this is, screenshots/demo gif, how to run
```

**Tech stack:** FastAPI + Postgres/pgvector + Ollama (local LLM, e.g.
Llama 3.1/Qwen2.5 with JSON-mode/tool-calling) + a local embedding model
(sentence-transformers `all-MiniLM-L6-v2` or Ollama `nomic-embed-text`) +
scikit-learn (HDBSCAN/agglomerative) for clustering + Next.js/TanStack
Table for the frontend. For the hosted demo, `CloudProvider` swaps in a
free-tier API (e.g. Groq, which is fast and has a generous free tier and
supports tool-calling models) — the rest of the code is unchanged.

## Implementation Phases

1. **Scaffolding** — repo structure above, docker-compose skeleton
   (postgres+pgvector, ollama, empty backend/frontend containers), CI
   stub, README.
2. **Ingestion layer** — `ContentBlock` interface; PDF extractor (text +
   table extraction via pdfplumber/pymupdf, OCR fallback via pytesseract
   for scanned pages), image extractor (OCR), docx/pptx extractors. Store
   raw blocks with source doc/page/bbox in Postgres.
3. **Chunking + embedding** — chunk content blocks, embed, store in
   pgvector; a retrieval function used by both schema discovery and chat.
4. **Schema discovery engine** — candidate-field extraction per doc,
   embedding + clustering across a corpus, LLM cluster review producing
   canonical field name/definition + conflict flags. Expose as an API
   (propose schema for a batch of docs).
5. **Schema approval flow** — UI table to review/rename/merge/split/
   reject proposed fields (+ same actions reachable via chat agent tools);
   support user-seeded target fields as an alternative entry point.
6. **Extraction + normalization engine** — structured extraction of an
   approved schema against each doc (retrieval-augmented, JSON output),
   unit/scale normalization, confidence scoring, provenance citations,
   review-queue population for non-mechanical cases.
7. **Chat agent** — tool-calling agent wired to the schema/extraction/
   query/export functions above, so the user can drive everything
   conversationally, not just through the UI.
8. **Unified table UI + export** — data grid over the unified table with
   per-cell provenance popovers and a review-queue view; CSV/XLSX/Parquet
   export.
9. **LLMProvider abstraction + hosted demo** — implement `CloudProvider`
   against a free-tier API, deploy frontend (Vercel free tier) + backend
   (Render/Fly.io free tier) using it; keep local Ollama path as the
   default in the Docker Compose / README instructions.
10. *(Fast-follow, not in this plan's critical path)* — recommendation
    layer: given an approved schema + summary stats, LLM suggests
    downstream uses of the unified dataset.

Each phase should land with its own tests (extractor unit tests against
sample files, a synthetic mini-corpus of fake "investor report" PDFs with
deliberately varied field names/units/scales to exercise the clustering
and normalization logic end-to-end) before moving to the next.

## Verification

- Unit tests per ingestion extractor against representative sample files
  (a normal text PDF, a scanned/OCR PDF, an image, a docx/pptx).
- An end-to-end test corpus: a handful of synthetic "investor report"
  PDFs built specifically to vary field naming ("Revenue" vs "Net Sales"),
  units ($K vs $M), and methodology (GAAP vs non-GAAP) — run the full
  pipeline (ingest → discover schema → approve → extract → normalize) and
  assert the unified table and conflict flags come out correct.
- Manual run via `docker compose up` → upload the test corpus through the
  UI/chat → confirm schema proposal, approval, extraction, and export all
  work, and that provenance popovers point at the correct source snippet.
- Hosted demo smoke test: same corpus through the deployed instance using
  `CloudProvider`.
