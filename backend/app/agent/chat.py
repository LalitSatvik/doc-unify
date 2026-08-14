"""Tool-calling chat loop: lets the user drive schema discovery,
approval, extraction, and querying conversationally instead of only
through the UI. Every tool call reuses the same logic the REST API
uses (see `app.agent.tools`)."""

from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.agent.tools import TOOL_DEFINITIONS, call_tool
from app.llm.base import LLMProvider

MAX_TOOL_ITERATIONS = 5

SYSTEM_PROMPT = (
    "You are an assistant that helps the user unify data extracted from "
    "heterogeneous documents into one structured table. Use the available "
    "tools to inspect uploaded documents, propose and approve a schema, "
    "run extraction, and answer questions about the resulting table -- "
    "cite exactly where a value came from via explain_cell when asked. "
    "Never fabricate a value; only report what the tools return."
)


async def run_agent_turn(
    session: Session, llm_provider: LLMProvider, messages: list[dict[str, str]]
) -> str:
    conversation: list[dict[str, str]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *messages,
    ]

    for _ in range(MAX_TOOL_ITERATIONS):
        response = await llm_provider.complete(conversation, tools=TOOL_DEFINITIONS)

        if not response.tool_calls:
            return response.text or ""

        conversation.append({"role": "assistant", "content": response.text or ""})
        for call in response.tool_calls:
            result = await call_tool(
                call.name, call.arguments, session=session, llm_provider=llm_provider
            )
            conversation.append({"role": "tool", "content": json.dumps(result)})

    return "I wasn't able to finish that within the allowed number of tool calls."
