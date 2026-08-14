# doc-unify

Feed it messy, heterogeneous documents (investor reports, PDFs, images,
docx/pptx — video coming later) and it figures out what structured data
can be pulled out of them, proposes **one unified schema across the whole
corpus** (catching when "Revenue" and "Net Sales" are the same metric,
and flagging when they only look the same), lets you approve/adjust that
schema conversationally, then extracts every document against it with
full provenance (source doc/page/snippet per cell) and confidence
scoring.

Built entirely with free, local tools — Ollama for the LLM and
embeddings, Postgres+pgvector for storage/retrieval — so it runs fully
offline via Docker Compose. `CloudProvider` (an OpenAI-compatible client,
e.g. for Groq's free tier) implements the same `LLMProvider` interface as
`OllamaProvider`, so a hosted deployment is a config change
(`LLM_PROVIDER=cloud` + `CLOUD_*` env vars), not a code change.

## Why

Manually unifying data across hundreds of investor reports — each with a
different layout, different field names for the same metric, different
units, sometimes different accounting methodology — is slow and
error-prone. This project automates the two hard parts: figuring out
*what's extractable* across an unfamiliar corpus, and reconciling
differently-labeled fields into one consistent table without silently
merging things that only look alike.

## Status

The full pipeline is implemented end to end: ingest (PDF/image/docx/pptx,
with OCR fallback for scans) → chunk + embed into pgvector → propose a
unified schema (candidate extraction → clustering → LLM cluster review,
with explicit conflict flags) → approve/rename fields → extract +
normalize against the approved schema (unit/scale conversion, confidence
scoring, a review queue for anything that can't be mechanically
normalized) → query it all conversationally through a tool-calling chat
agent, or through the ledger-themed frontend. Video ingestion remains an
explicitly deferred stub (`app/ingestion/video.py`) against the same
`Extractor` interface.

Backend: 74 tests, `ruff` clean. Frontend: `next build` (TypeScript +
ESLint) clean.

## Architecture

```
backend/app/
  ingestion/   per-format extractors -> common ContentBlock interface
  embedding/   chunking + pgvector retrieval
  schema/      candidate-field extraction, clustering, LLM cluster review
  extraction/  structured extraction against an approved schema + normalization
  agent/       tool-calling chat agent over the above
  llm/         LLMProvider interface (OllamaProvider / CloudProvider)
  db/          models + migrations
  api/         FastAPI routes
frontend/      Next.js app (upload, chat, schema review, unified data grid)
```

## Running locally

```bash
docker compose up --build

# first run only -- pull the models Ollama needs:
docker compose exec ollama ollama pull qwen2.5:7b
docker compose exec ollama ollama pull nomic-embed-text
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- Ollama: http://localhost:11434

## Running the backend tests

```bash
cd backend
pip install -e ".[dev]"
pytest
ruff check .
```

## License

MIT
