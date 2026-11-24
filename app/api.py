from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Report
from app.schemas import EventAccepted, EventIn, ReportOut
from app.services.pipeline import ReportPipeline, create_pending_report

router = APIRouter()


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.db.session_factory() as session:
        yield session


def get_pipeline(request: Request) -> ReportPipeline:
    return request.app.state.pipeline


SessionDep = Annotated[AsyncSession, Depends(get_session)]
PipelineDep = Annotated[ReportPipeline, Depends(get_pipeline)]


@router.get("/health", tags=["ops"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post(
    "/events",
    response_model=EventAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["events"],
    summary="Receive an event and start generating a report",
)
async def receive_event(
    event: EventIn,
    background: BackgroundTasks,
    session: SessionDep,
    pipeline: PipelineDep,
) -> EventAccepted:
    report = await create_pending_report(session, event.customer_id, event.type)
    background.add_task(pipeline.process, report.id)
    return EventAccepted(report_id=report.id, status=report.status)


@router.get("/reports/{report_id}", response_model=ReportOut, tags=["reports"])
async def get_report(report_id: str, session: SessionDep) -> Report:
    report = await session.get(Report, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.get("/reports", response_model=list[ReportOut], tags=["reports"])
async def list_reports(
    session: SessionDep,
    customer_id: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[Report]:
    query = select(Report).order_by(Report.created_at.desc()).limit(limit)
    if customer_id:
        query = query.where(Report.customer_id == customer_id)
    result = await session.execute(query)
    return list(result.scalars())
