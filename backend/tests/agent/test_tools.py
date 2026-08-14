from app.agent.tools import TOOL_DEFINITIONS, call_tool
from app.db.models import SchemaField
from app.db.models import TableCell as TableCellRow
from app.db.repository import create_document


def test_tool_definitions_cover_the_expected_names() -> None:
    names = {t.name for t in TOOL_DEFINITIONS}
    assert names == {
        "list_documents",
        "propose_schema",
        "approve_schema_field",
        "run_extraction",
        "query_table",
        "explain_cell",
        "export_table",
    }


async def test_list_documents_returns_uploaded_documents(session) -> None:
    create_document(session, filename="report.pdf", content_type="application/pdf")

    result = await call_tool("list_documents", {}, session=session, llm_provider=None)

    assert len(result["documents"]) == 1
    assert result["documents"][0]["filename"] == "report.pdf"


async def test_approve_schema_field_updates_status_and_name(session) -> None:
    field = SchemaField(name="Total Revenue", definition="Revenue", member_labels=[])
    session.add(field)
    session.flush()

    result = await call_tool(
        "approve_schema_field",
        {"field_id": field.id, "name": "Revenue"},
        session=session,
        llm_provider=None,
    )

    assert result["status"] == "approved"
    assert result["name"] == "Revenue"


async def test_explain_cell_returns_provenance(session) -> None:
    document = create_document(session, filename="report.pdf", content_type="application/pdf")
    field = SchemaField(name="Total Revenue", definition="Revenue", member_labels=[])
    session.add(field)
    session.flush()
    cell = TableCellRow(
        document_id=document.id,
        schema_field_id=field.id,
        raw_value="12,345",
        raw_unit="$K",
        normalized_value=12_345_000.0,
        confidence=0.9,
        source_snippet="Total Revenue: $12,345K",
        page=3,
        needs_review=False,
    )
    session.add(cell)
    session.flush()

    result = await call_tool("explain_cell", {"cell_id": cell.id}, session=session, llm_provider=None)

    assert result["document_filename"] == "report.pdf"
    assert result["field_name"] == "Total Revenue"
    assert result["page"] == 3
    assert result["source_snippet"] == "Total Revenue: $12,345K"


async def test_query_table_returns_unified_grid(session) -> None:
    document = create_document(session, filename="report.pdf", content_type="application/pdf")
    field = SchemaField(name="Total Revenue", definition="Revenue", member_labels=[])
    session.add(field)
    session.flush()
    session.add(
        TableCellRow(
            document_id=document.id,
            schema_field_id=field.id,
            raw_value="12,345",
            raw_unit="$K",
            normalized_value=12_345_000.0,
            confidence=0.9,
            needs_review=False,
        )
    )
    session.flush()

    result = await call_tool("query_table", {}, session=session, llm_provider=None)

    assert len(result["rows"]) == 1
    assert result["rows"][0]["cells"]["Total Revenue"]["normalized_value"] == 12_345_000.0


async def test_export_table_returns_csv_text(session) -> None:
    document = create_document(session, filename="report.pdf", content_type="application/pdf")
    field = SchemaField(name="Total Revenue", definition="Revenue", member_labels=[])
    session.add(field)
    session.flush()
    session.add(
        TableCellRow(
            document_id=document.id,
            schema_field_id=field.id,
            raw_value="12,345",
            normalized_value=12_345_000.0,
            confidence=0.9,
            needs_review=False,
        )
    )
    session.flush()

    result = await call_tool("export_table", {}, session=session, llm_provider=None)

    assert "report.pdf" in result["csv"]
    assert "Total Revenue" in result["csv"]
