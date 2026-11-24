from collections.abc import AsyncIterator

import httpx
import pytest

from app.config import Settings
from app.main import create_app
from app.services.llm import FakeLLMClient, LLMClient


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(database_url=f"sqlite+aiosqlite:///{tmp_path / 'test.db'}", llm_provider="fake")


async def _client_for(app) -> AsyncIterator[httpx.AsyncClient]:
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


@pytest.fixture
async def client(settings) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app(settings=settings, llm=FakeLLMClient())
    async for c in _client_for(app):
        yield c


@pytest.fixture
def make_client(settings):
    """Build a client around a custom LLM client (e.g. one that fails)."""

    async def factory(llm: LLMClient) -> AsyncIterator[httpx.AsyncClient]:
        app = create_app(settings=settings, llm=llm)
        async for c in _client_for(app):
            yield c

    return factory
