from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.utils.texts import get_text
from app.utils.telegram import answer_with_preview

router = Router(name="help")


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await answer_with_preview(message, get_text("help.text"))
