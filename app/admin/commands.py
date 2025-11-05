from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.admin.filters import RoleFilter

router = Router(name="admin")
router.message.filter(RoleFilter({"admin", "moderator"}))


@router.message(Command("admin"))
async def admin_help(message: Message) -> None:
    await message.answer("Админ-команды будут добавлены позднее.")
