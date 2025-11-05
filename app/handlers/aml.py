from __future__ import annotations

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from datetime import datetime

from app.fsm.aml import AMLCheckState
from app.keyboards.aml import build_aml_menu, build_aml_result
from app.services.aml.service import AMLService
from app.utils.texts import get_text

router = Router(name="aml")


@router.callback_query(lambda c: c.data == "aml")
async def open_aml_menu(callback: CallbackQuery) -> None:
    await callback.message.edit_text(get_text("aml.title"), reply_markup=build_aml_menu())
    await callback.answer()


@router.callback_query(lambda c: c.data == "aml:policy")
async def show_policy(callback: CallbackQuery) -> None:
    from app.keyboards.common import nav_row

    await callback.message.edit_text(
        get_text("aml.policy"), reply_markup=nav_row().as_markup()
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "aml:check:start")
async def aml_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(AMLCheckState.input_address)
    await callback.message.edit_text(get_text("aml.form.prompt"))
    await callback.answer()


@router.message(AMLCheckState.input_address)
async def aml_process_address(message: Message, state: FSMContext, aml_service: AMLService) -> None:
    address = message.text.strip()
    await state.set_state(AMLCheckState.validating)
    await message.answer(get_text("aml.form.validating"))
    try:
        result = await aml_service.check_address(address)
    except Exception as exc:
        # Show error to the user and return to input state
        await state.set_state(AMLCheckState.input_address)
        await message.answer(f"Ошибка AML: {exc}\nВведите адрес ещё раз")
        return
    await state.update_data(result=result)
    await state.set_state(AMLCheckState.result)
    risk = result.get("risk_level", "unknown")
    chain = result.get("chain") or "—"
    score = result.get("score")
    time_str = result.get("resultDate") or result.get("initDate")
    # format time to human-friendly string
    formatted_time = None
    if time_str:
        try:
            dt = datetime.fromisoformat(str(time_str))
            # present in local timezone with readable name and offset
            formatted_time = dt.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z %z")
        except Exception:
            formatted_time = str(time_str)
    addr = result.get("address")
    parts = [
        f"🛡️ Риск: <b>{risk}</b>",
    ]
    if formatted_time:
        parts.append(f"⏱ Время: {formatted_time}")
    parts.extend([
        f"🔗 Адрес: <code>{addr}</code>",
        f"⛓ Сеть: <b>{chain}</b>",
        f"📊 Риск: {score if score is not None else '—'}",
    ])
    share = result.get("shareLink")
    if share:
        parts.append(f"🔗 <a href=\"{share}\">Share</a>")
    await message.answer("\n".join(parts), reply_markup=build_aml_result())


@router.callback_query(lambda c: c.data == "aml:result:export")
async def aml_export(callback: CallbackQuery, state: FSMContext, aml_service: AMLService) -> None:
    data = await state.get_data()
    result = data.get("result")
    if not result:
        await callback.answer("Нет отчёта", show_alert=True)
        return
    payload = await aml_service.export_report(result)
    document = BufferedInputFile(payload, filename="aml_report.json")
    await callback.message.answer_document(document=document)
    await callback.answer()
