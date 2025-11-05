from __future__ import annotations

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.fsm.lead import LeadFormState
from app.keyboards.lead import build_lead_confirm
from app.services.leads.service import LeadRequest, LeadService
from app.utils.texts import get_text

router = Router(name="leads")


@router.callback_query(lambda c: c.data == "lead:form:start")
async def start_lead_form(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(LeadFormState.contact)
    await callback.message.edit_text(get_text("lead.form.contact"))
    await callback.answer()


@router.message(LeadFormState.contact)
async def process_contact(message: Message, state: FSMContext) -> None:
    await state.update_data(contact=message.text.strip())
    await state.set_state(LeadFormState.experience)
    await message.answer(get_text("lead.form.experience"))


@router.message(LeadFormState.experience)
async def process_experience(message: Message, state: FSMContext) -> None:
    await state.update_data(experience=message.text.strip())
    await state.set_state(LeadFormState.requisites)
    await message.answer(get_text("lead.form.requisites"))


@router.message(LeadFormState.requisites)
async def process_requisites(message: Message, state: FSMContext) -> None:
    await state.update_data(requisites=message.text.strip())
    await state.set_state(LeadFormState.confirm)
    data = await state.get_data()
    summary = get_text("lead.form.summary").format(
        contact=data.get("contact"),
        experience=data.get("experience"),
        requisites=data.get("requisites"),
    )
    await message.answer(summary, reply_markup=build_lead_confirm())


@router.callback_query(lambda c: c.data == "lead:form:restart")
async def restart_form(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(LeadFormState.contact)
    await callback.message.edit_text(get_text("lead.form.contact"))
    await callback.answer()


@router.callback_query(lambda c: c.data == "lead:form:submit")
async def submit_lead(callback: CallbackQuery, state: FSMContext, lead_service: LeadService) -> None:
    data = await state.get_data()
    payload = LeadRequest(
        tg_id=callback.from_user.id,
        contact=str(data.get("contact", "")),
        experience=str(data.get("experience", "")),
        sber_requisites_count=int(str(data.get("requisites", "0")) or 0),
        consent=True,
    )
    lead_id = await lead_service.create_lead(payload)
    await callback.message.edit_text(get_text("lead.form.done").format(id=lead_id))
    await state.clear()
    await callback.answer()
