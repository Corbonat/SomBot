from __future__ import annotations

from aiogram import Dispatcher

from app.handlers import aml, help, leads, menu, rates, start
from app.handlers import fallback
from app.admin import commands as admin_commands


def register_handlers(dp: Dispatcher) -> None:
    routers = [
        start.router,
        help.router,
        menu.router,
        rates.router,
        aml.router,
        leads.router,
        admin_commands.router,
        # Fallback must be last
        fallback.router,
    ]
    for router in routers:
        dp.include_router(router)
