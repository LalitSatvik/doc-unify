"""Tool definitions + dispatcher the chat agent calls into. Every tool
reuses the same schema-discovery/extraction/query logic the REST API uses
-- the agent is another caller of that logic, not a separate path."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Document, SchemaField, SchemaFieldStatus
from app.db.models import TableCell as TableCellRow
from app.extraction.run import run_extraction
from app.extraction.table import build_unified_table, unified_table_to_csv
from app.llm.base import LLMProvider, ToolDefinition
from app.schema.discover import discover_schema

TOOL_DEFINITIONS: list[ToolDefinition] = [
    ToolDefinition(
        name="list_documents",
        description="List every uploaded document with its ingestion status.",
        parameters={"type": "object", "properties": {}},
    ),
    ToolDefinition(
        name="propose_schema",
        description="Run schema discovery over a set of documents and propose unified fields.",
        parameters={
            "type": "object",
            "properties": {
                "document_ids": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["document_ids"],
        },
    ),
    ToolDefinition(
        name="approve_schema_field",
        description="Approve (and optionally rename) a proposed schema field.",
        parameters={
            "type": "object",
            "properties": {
                "field_id": {"type": "string"},
                "name": {"type": "string"},
            },
            "required": ["field_id"],
        },
    ),
    ToolDefinition(
        name="run_extraction",
        description="Extract approved schema fields' values from a set of documents.",
        parameters={
            "type": "object",
            "properties": {
                "document_ids": {"type": "array", "items": {"type": "string"}},
                "schema_field_ids": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["document_ids", "schema_field_ids"],
        },
    ),
    ToolDefinition(
        name="query_table",
        description="Return the current unified table: one row per document, one column per field.",
        parameters={"type": "object", "properties": {}},
    ),
    ToolDefinition(
        name="explain_cell",
        description="Explain where one extracted cell's value came from (document, page, snippet).",
        parameters={
            "type": "object",
            "properties": {"cell_id": {"type": "string"}},
            "required": ["cell_id"],
        },
    ),
    ToolDefinition(
        name="export_table",
        description="Export the current unified table as CSV text.",
        parameters={"type": "object", "properties": {}},
    ),
]


async def call_tool(
    name: str, arguments: dict[str, Any], *, session: Session, llm_provider: LLMProvider | None
) -> dict[str, Any]:
    handler = _HANDLERS.get(name)
    if handler is None:
        return {"error": f"Unknown tool: {name}"}
    return await handler(arguments, session, llm_provider)


async def _list_documents(args: dict, session: Session, llm_provider: LLMProvider | None) -> dict:
    documents = session.scalars(select(Document)).all()
    return {
        "documents": [
            {"id": d.id, "filename": d.filename, "status": d.status.value} for d in documents
        ]
    }


async def _propose_schema(args: dict, session: Session, llm_provider: LLMProvider | None) -> dict:
    fields = await discover_schema(session, llm_provider, args["document_ids"])
    session.commit()
    return {
        "fields": [
            {
                "id": f.id,
                "name": f.name,
                "definition": f.definition,
                "has_conflict": f.has_conflict,
                "conflict_reason": f.conflict_reason,
            }
            for f in fields
        ]
    }


async def _approve_schema_field(args: dict, session: Session, llm_provider: LLMProvider | None) -> dict:
    field = session.get(SchemaField, args["field_id"])
    if field is None:
        return {"error": "Schema field not found"}
    if args.get("name"):
        field.name = args["name"]
    field.status = SchemaFieldStatus.APPROVED
    session.commit()
    return {"id": field.id, "name": field.name, "status": field.status.value}


async def _run_extraction(args: dict, session: Session, llm_provider: LLMProvider | None) -> dict:
    cells = await run_extraction(
        session, llm_provider, args["document_ids"], args["schema_field_ids"]
    )
    session.commit()
    return {
        "cells_extracted": len(cells),
        "needs_review": sum(1 for c in cells if c.needs_review),
    }


async def _query_table(args: dict, session: Session, llm_provider: LLMProvider | None) -> dict:
    return {"rows": build_unified_table(session)}


async def _explain_cell(args: dict, session: Session, llm_provider: LLMProvider | None) -> dict:
    cell = session.get(TableCellRow, args["cell_id"])
    if cell is None:
        return {"error": "Table cell not found"}
    document = session.get(Document, cell.document_id)
    field = session.get(SchemaField, cell.schema_field_id)
    return {
        "document_filename": document.filename if document else None,
        "field_name": field.name if field else None,
        "raw_value": cell.raw_value,
        "raw_unit": cell.raw_unit,
        "normalized_value": cell.normalized_value,
        "confidence": cell.confidence,
        "page": cell.page,
        "source_snippet": cell.source_snippet,
    }


async def _export_table(args: dict, session: Session, llm_provider: LLMProvider | None) -> dict:
    return {"csv": unified_table_to_csv(build_unified_table(session))}


_HANDLERS = {
    "list_documents": _list_documents,
    "propose_schema": _propose_schema,
    "approve_schema_field": _approve_schema_field,
    "run_extraction": _run_extraction,
    "query_table": _query_table,
    "explain_cell": _explain_cell,
    "export_table": _export_table,
}
