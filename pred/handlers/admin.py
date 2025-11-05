from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.admin.filters import RoleFilter

router = Router(name="pred-admin")
router.message.filter(RoleFilter({"admin"}))


@router.message(Command("schedule"))
async def toggle_schedule(message: Message) -> None:
    await message.answer("Автопостинг будет настроен позже.")


@router.message(Command("seed"))
async def seed_phrase(message: Message) -> None:
    await message.answer("Добавление фраз пока не реализовано.")
