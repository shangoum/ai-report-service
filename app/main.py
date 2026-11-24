import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import router
from app.config import Settings, get_settings
from app.db import Database
from app.services.crm import CustomerSource, JsonCustomerSource
from app.services.llm import LLMClient, build_llm_client
from app.services.pipeline import ReportPipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def create_app(
    settings: Settings | None = None,
    llm: LLMClient | None = None,
    customers: CustomerSource | None = None,
) -> FastAPI:
    """App factory. Tests inject their own settings, LLM client and customer source."""
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        db = Database(settings.database_url)
        await db.create_tables()
        llm_client = llm or build_llm_client(settings)
        app.state.db = db
        app.state.pipeline = ReportPipeline(
            session_factory=db.session_factory,
            customers=customers or JsonCustomerSource(),
            llm=llm_client,
            max_messages=settings.max_messages_in_context,
        )
        yield
        if hasattr(llm_client, "aclose"):
            await llm_client.aclose()
        await db.dispose()

    app = FastAPI(
        title="AI Report Service",
        description="Turns an incoming customer event into an AI-generated advisor report.",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.include_router(router)
    return app


app = create_app()
