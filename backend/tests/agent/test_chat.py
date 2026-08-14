import json

from app.agent.chat import run_agent_turn
from app.db.models import SchemaField, SchemaFieldStatus
from app.llm.base import LLMResponse, ToolCall
from tests.support.scripted_llm import ScriptedLLMProvider


async def test_agent_executes_tool_call_and_returns_final_text(session) -> None:
    field = SchemaField(name="Total Revenue", definition="Revenue", member_labels=[])
    session.add(field)
    session.flush()

    provider = ScriptedLLMProvider(
        complete_responses=[
            LLMResponse(
                text="",
                tool_calls=[ToolCall(name="approve_schema_field", arguments={"field_id": field.id}, id="1")],
            ),
            LLMResponse(text="Approved Total Revenue."),
        ]
    )

    reply = await run_agent_turn(session, provider, [{"role": "user", "content": "approve revenue"}])

    assert reply == "Approved Total Revenue."
    assert field.status == SchemaFieldStatus.APPROVED
    assert len(provider.complete_calls) == 2

    second_call_messages = provider.complete_calls[1]
    tool_messages = [m for m in second_call_messages if m["role"] == "tool"]
    assert len(tool_messages) == 1
    assert json.loads(tool_messages[0]["content"])["status"] == "approved"


async def test_agent_returns_text_directly_when_no_tool_call_needed(session) -> None:
    provider = ScriptedLLMProvider(complete_responses=[LLMResponse(text="Hi, how can I help?")])

    reply = await run_agent_turn(session, provider, [{"role": "user", "content": "hello"}])

    assert reply == "Hi, how can I help?"
    assert len(provider.complete_calls) == 1


async def test_agent_stops_after_max_tool_iterations(session) -> None:
    looping_call = LLMResponse(
        text="",
        tool_calls=[ToolCall(name="list_documents", arguments={}, id="x")],
    )
    provider = ScriptedLLMProvider(complete_responses=[looping_call] * 5)

    reply = await run_agent_turn(session, provider, [{"role": "user", "content": "loop forever"}])

    assert "unable" in reply.lower() or "couldn't" in reply.lower() or "wasn't able" in reply.lower()
    assert len(provider.complete_calls) == 5
