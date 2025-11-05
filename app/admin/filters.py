from __future__ import annotations

from typing import Iterable

from aiogram.filters import BaseFilter
from aiogram.types import Message


class RoleFilter(BaseFilter):
    def __init__(self, roles: Iterable[str]) -> None:
        self.roles = set(roles)

    async def __call__(self, message: Message, roles: dict[int, str] | None = None) -> bool:
        if roles is None:
            return False
        role = roles.get(message.from_user.id)
        return role in self.roles
