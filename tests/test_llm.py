import json

import httpx
import pytest

from app.config import Settings
from app.services.llm import FakeLLMClient, LLMError, OpenAICompatibleClient, build_llm_client


def _settings(**kwargs) -> Settings:
    return Settings(llm_provider="openai", llm_api_key="test-key", llm_model="test-model", **kwargs)


async def test_openai_client_sends_prompt_and_returns_content():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["auth"] = request.headers["Authorization"]
        captured["body"] = json.loads(request.content)
        body = {"choices": [{"message": {"content": "  ## Summary\nok  "}}]}
        return httpx.Response(200, json=body)

    client = OpenAICompatibleClient(_settings(), transport=httpx.MockTransport(handler))
    result = await client.generate("system", "user data")
    await client.aclose()

    assert result == "## Summary\nok"
    assert captured["auth"] == "Bearer test-key"
    assert captured["body"]["model"] == "test-model"
    assert captured["body"]["messages"][1] == {"role": "user", "content": "user data"}


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        (httpx.Response(503), "HTTP 503"),
        (httpx.Response(200, json={"unexpected": True}), "Unexpected LLM response format"),
        (httpx.Response(200, json={"choices": [{"message": {"content": " "}}]}), "empty report"),
    ],
)
async def test_openai_client_errors_become_llm_error(response, expected):
    client = OpenAICompatibleClient(_settings(), transport=httpx.MockTransport(lambda _: response))
    with pytest.raises(LLMError, match=expected):
        await client.generate("system", "user")
    await client.aclose()


async def test_openai_client_network_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom")

    client = OpenAICompatibleClient(_settings(), transport=httpx.MockTransport(handler))
    with pytest.raises(LLMError, match="ConnectError"):
        await client.generate("system", "user")
    await client.aclose()


def test_openai_provider_requires_api_key():
    with pytest.raises(LLMError, match="LLM_API_KEY"):
        OpenAICompatibleClient(Settings(llm_provider="openai", llm_api_key=""))


def test_default_provider_is_fake():
    assert isinstance(build_llm_client(Settings(llm_provider="fake")), FakeLLMClient)
