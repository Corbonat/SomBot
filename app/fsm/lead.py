from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class LeadFormState(StatesGroup):
    contact = State()
    experience = State()
    requisites = State()
    confirm = State()
