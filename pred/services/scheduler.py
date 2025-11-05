from __future__ import annotations

from typing import Iterable, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler


class AutopostScheduler:
    def __init__(self) -> None:
        self.scheduler = AsyncIOScheduler()

    def configure(self, times: Iterable[str]) -> None:
        # TODO: configure jobs based on times and chat subscriptions.
        _ = list(times)

    async def start(self) -> None:
        if not self.scheduler.running:
            self.scheduler.start()

    async def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown()
