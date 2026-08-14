from fastapi.testclient import TestClient

from app.llm.base import LLMResponse
from app.llm.factory import get_llm_provider
from app.main import app
from tests.support.scripted_llm import ScriptedLLMProvider


def test_chat_returns_agent_reply(client: TestClient) -> None:
    provider = ScriptedLLMProvider(complete_responses=[LLMResponse(text="Hi, how can I help?")])
    app.dependency_overrides[get_llm_provider] = lambda: provider

    response = client.post("/chat", json={"messages": [{"role": "user", "content": "hello"}]})

    assert response.status_code == 200
    assert response.json()["reply"] == "Hi, how can I help?"
