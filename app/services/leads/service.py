from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


@dataclass
class LeadRequest:
    tg_id: int
    contact: str
    experience: str
    sber_requisites_count: int
    consent: bool


class LeadService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def create_lead(self, payload: LeadRequest) -> int:
        # TODO: persist lead into database, emit notification.
        async with self.session_factory() as session:
            _ = session  # placeholder usage to satisfy linters
        return 0

    async def notify(self, service_chat_id: Optional[int], text: str) -> None:
        # TODO: send notification to service chat via bot when configured.
        _ = (service_chat_id, text)
        return None
