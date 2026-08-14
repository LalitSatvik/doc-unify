"""Chat endpoint: one turn of the tool-calling agent."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agent.chat import run_agent_turn
from app.db.session import get_session
from app.llm.base import LLMProvider
from app.llm.factory import get_llm_provider

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]


class ChatResponse(BaseModel):
    reply: str


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    session: Session = Depends(get_session),
    llm_provider: LLMProvider = Depends(get_llm_provider),
) -> ChatResponse:
    reply = await run_agent_turn(
        session, llm_provider, [m.model_dump() for m in request.messages]
    )
    session.commit()
    return ChatResponse(reply=reply)
