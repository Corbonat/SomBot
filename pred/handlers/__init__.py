from __future__ import annotations

from aiogram import Dispatcher

from pred.handlers import admin, predict, start


def register_handlers(dp: Dispatcher) -> None:
    dp.include_router(start.router)
    dp.include_router(predict.router)
    dp.include_router(admin.router)
