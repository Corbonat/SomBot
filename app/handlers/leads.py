from __future__ import annotations

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.fsm.lead import LeadFormState
from app.keyboards.lead import (
    build_lead_confirm,
    build_lead_done_keyboard,
    build_lead_menu,
    build_lead_question_keyboard,
)
from app.services.leads.service import LeadRequest, LeadService
from app.utils.texts import get_text
from app.utils.telegram import answer_with_preview, edit_text_or_caption

router = Router(name="leads")


@router.callback_query(lambda c: c.data == "lead:form:start")
async def start_lead_form(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(LeadFormState.contact)
    await edit_text_or_caption(
        callback.message,
        get_text("lead.form.contact"),
        build_lead_question_keyboard(),
        with_preview=False,
    )
    await callback.answer()


@router.message(LeadFormState.contact)
async def process_contact(message: Message, state: FSMContext) -> None:
    await state.update_data(contact=message.text.strip())
    await state.set_state(LeadFormState.experience)
    await answer_with_preview(
        message,
        get_text("lead.form.experience"),
        reply_markup=build_lead_question_keyboard(),
        with_preview=False,
    )


@router.message(LeadFormState.experience)
async def process_experience(message: Message, state: FSMContext) -> None:
    await state.update_data(experience=message.text.strip())
    await state.set_state(LeadFormState.requisites)
    await answer_with_preview(
        message,
        get_text("lead.form.requisites"),
        reply_markup=build_lead_question_keyboard(),
        with_preview=False,
    )


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
    await answer_with_preview(
        message,
        summary,
        reply_markup=build_lead_confirm(),
        with_preview=False,
    )


@router.callback_query(lambda c: c.data == "lead:form:restart")
async def restart_form(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(LeadFormState.contact)
    await edit_text_or_caption(
        callback.message,
        get_text("lead.form.contact"),
        build_lead_question_keyboard(),
        with_preview=False,
    )
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
    await lead_service.create_lead(payload)
    await edit_text_or_caption(
        callback.message,
        get_text("lead.form.done"),
        build_lead_done_keyboard(),
        with_preview=False,
    )
    await state.clear()
    await callback.answer()


@router.callback_query(lambda c: c.data == "lead:form:cancel")
async def cancel_lead_form(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await edit_text_or_caption(
        callback.message,
        get_text("lead.promo"),
        build_lead_menu(),
        replace_media=True,
    )
    await callback.answer("Опрос прерван")
