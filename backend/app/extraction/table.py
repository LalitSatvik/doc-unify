"""Builds the unified table (one row per document, one column per schema
field) and its CSV serialization -- shared by the REST API and the chat
agent's `query_table`/`export_table` tools."""

from __future__ import annotations

import csv
import io

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Document, SchemaField
from app.db.models import TableCell as TableCellRow


def build_unified_table(session: Session) -> list[dict]:
    documents = {d.id: d for d in session.scalars(select(Document)).all()}
    fields = {f.id: f for f in session.scalars(select(SchemaField)).all()}
    cells = session.scalars(select(TableCellRow)).all()

    rows: dict[str, dict] = {}
    for cell in cells:
        document = documents.get(cell.document_id)
        field = fields.get(cell.schema_field_id)
        if document is None or field is None:
            continue

        row = rows.setdefault(
            document.id,
            {"document_id": document.id, "document_filename": document.filename, "cells": {}},
        )
        row["cells"][field.name] = {
            "raw_value": cell.raw_value,
            "raw_unit": cell.raw_unit,
            "normalized_value": cell.normalized_value,
            "confidence": cell.confidence,
            "needs_review": cell.needs_review,
            "page": cell.page,
            "source_snippet": cell.source_snippet,
        }

    return list(rows.values())


def unified_table_to_csv(table: list[dict]) -> str:
    field_names = sorted({name for row in table for name in row["cells"]})

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["document", *field_names])
    for row in table:
        writer.writerow(
            [row["document_filename"]]
            + [row["cells"].get(name, {}).get("normalized_value", "") for name in field_names]
        )
    return buffer.getvalue()
