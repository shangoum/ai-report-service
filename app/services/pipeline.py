"""The report workflow: event -> customer data -> context -> LLM -> stored report."""

import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import Report, ReportStatus
from app.services.context import SYSTEM_PROMPT, build_context
from app.services.crm import CustomerNotFoundError, CustomerSource
from app.services.llm import LLMClient, LLMError

logger = logging.getLogger(__name__)


async def create_pending_report(session: AsyncSession, customer_id: str, event_type: str) -> Report:
    report = Report(customer_id=customer_id, event_type=event_type)
    session.add(report)
    await session.commit()
    await session.refresh(report)
    return report


class ReportPipeline:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        customers: CustomerSource,
        llm: LLMClient,
        max_messages: int,
    ) -> None:
        self._session_factory = session_factory
        self._customers = customers
        self._llm = llm
        self._max_messages = max_messages

    async def process(self, report_id: str) -> None:
        """Generate the report and record the outcome. Never raises: failures are stored."""
        async with self._session_factory() as session:
            report = await session.get(Report, report_id)
            if report is None:
                logger.error("Report %s disappeared before processing", report_id)
                return

            try:
                customer = await self._customers.get_customer(report.customer_id)
                context = build_context(customer, self._max_messages)
                report.content = await self._llm.generate(SYSTEM_PROMPT, context)
                report.status = ReportStatus.COMPLETED
                report.error = None
                logger.info("Report %s completed for %s", report_id, report.customer_id)
            except (CustomerNotFoundError, LLMError) as exc:
                self._reject(report, str(exc))
            except Exception:
                logger.exception("Unexpected error while processing report %s", report_id)
                self._reject(report, "Internal error while generating the report")

            await session.commit()

    @staticmethod
    def _reject(report: Report, reason: str) -> None:
        logger.warning("Report %s rejected: %s", report.id, reason)
        report.status = ReportStatus.FAILED
        report.error = reason
