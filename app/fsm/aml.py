from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class AMLCheckState(StatesGroup):
    input_address = State()
    validating = State()
    result = State()
    saving = State()
