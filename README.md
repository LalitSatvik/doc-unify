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
offline via Docker Compose. A hosted demo (see `/deploy`) swaps in a
free-tier cloud LLM behind the same provider interface.

## Why

Manually unifying data across hundreds of investor reports — each with a
different layout, different field names for the same metric, different
units, sometimes different accounting methodology — is slow and
error-prone. This project automates the two hard parts: figuring out
*what's extractable* across an unfamiliar corpus, and reconciling
differently-labeled fields into one consistent table without silently
merging things that only look alike.

## Status

Early scaffolding — see `docs/plan.md` for the phased build plan.

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
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- Ollama: http://localhost:11434 (pulls models on first run)

## License

MIT
