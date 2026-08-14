"""Schema discovery + approval: run discovery over a batch of documents,
list proposed/approved/rejected fields, and approve/rename/reject them."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import SchemaField, SchemaFieldStatus
from app.db.session import get_session
from app.llm.base import LLMProvider
from app.llm.factory import get_llm_provider
from app.schema.discover import discover_schema

router = APIRouter(prefix="/schema", tags=["schema"])


class SchemaFieldOut(BaseModel):
    id: str
    name: str
    definition: str
    status: SchemaFieldStatus
    has_conflict: bool
    conflict_reason: str | None
    member_labels: list[str]

    model_config = {"from_attributes": True}


class DiscoverRequest(BaseModel):
    document_ids: list[str]


class SchemaFieldPatch(BaseModel):
    name: str | None = None
    status: SchemaFieldStatus | None = None


@router.post("/discover", response_model=list[SchemaFieldOut])
async def discover(
    request: DiscoverRequest,
    session: Session = Depends(get_session),
    llm_provider: LLMProvider = Depends(get_llm_provider),
) -> list[SchemaField]:
    fields = await discover_schema(session, llm_provider, request.document_ids)
    session.commit()
    return fields


@router.get("/fields", response_model=list[SchemaFieldOut])
async def list_fields(session: Session = Depends(get_session)) -> list[SchemaField]:
    return list(session.scalars(select(SchemaField)).all())


@router.patch("/fields/{field_id}", response_model=SchemaFieldOut)
async def patch_field(
    field_id: str, patch: SchemaFieldPatch, session: Session = Depends(get_session)
) -> SchemaField:
    field = session.get(SchemaField, field_id)
    if field is None:
        raise HTTPException(status_code=404, detail="Schema field not found")

    if patch.name is not None:
        field.name = patch.name
    if patch.status is not None:
        field.status = patch.status

    session.commit()
    return field
