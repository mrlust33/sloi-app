import asyncio
import json
import uuid
import logging
import html
import traceback
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton, 
    ReplyKeyboardMarkup, KeyboardButton, 
    WebAppInfo
)

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# ЖЕСТКИЕ КОНСТАНТЫ ПРОЕКТА
BOT_TOKEN = "8765647186:AAGez9_BPRed47X2tp-QBc9MVERmxrOUkqk"
ADMIN_ID = 5293518524
SUPPORT_LINK = "tg://user?id=5293518524"
WEB_APP_URL = "https://mrlust33.github.io/sloi-app/?v=13.0"

SBP_PHONE = "+7 (977) 627-44-42"
SBP_BANK = "Т-Банк / Сбербанк"
SBP_RECEIVER = "Андрей А."

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# База данных заказов в памяти
orders_db = {}

@dp.message(CommandStart())
async def command_start_handler(message: types.Message):
    reply_kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🧁 Открыть меню", web_app=WebAppInfo(url=WEB_APP_URL))]],
        resize_keyboard=True
    )
    inline_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Уточнить детали / Поддержка 💬", url=SUPPORT_LINK)]
    ])
    
    text = (
        "SweetSpot | Доставка десертов\n"
        "Премиальные трайфлы ручной работы. Доставляем свежие партии по субботам ✨"
    )
    await message.answer(text, reply_markup=reply_kb, parse_mode="HTML")


@dp.message(F.web_app_data)
async def web_app_data_handler(message: types.Message):
    try:
        data = json.loads(message.web_app_data.data)
        order_id = uuid.uuid4().hex[:8].upper()
        
        # Строгое извлечение данных
        cart_items = data.get('cart', [])
        total_price = data.get('totalPrice', 0)
        phone_raw = data.get('phone', 'Не указан')
        customer_name_raw = data.get('name', 'Не указан')
        delivery_date_raw = data.get('delivery_date', 'Не указана')
        tg_username_raw = data.get('tg_username', 'Не указан')
        tg_id = data.get('tg_id')
        addr = data.get('address', {})

        # 1. ТОТАЛЬНОЕ ЭКРАНИРОВАНИЕ ДАННЫХ ДЛЯ HTML
        safe_phone = html.escape(str(phone_raw))
        safe_name = html.escape(str(customer_name_raw))
        safe_date = html.escape(str(delivery_date_raw))
        safe_username = html.escape(str(tg_username_raw).replace('@', ''))
        
        safe_street = html.escape(str(addr.get('street', '')))
        safe_house = html.escape(str(addr.get('house', '')))
        safe_entrance = html.escape(str(addr.get('entrance', '')))
        safe_floor = html.escape(str(addr.get('floor', '')))
        safe_flat = html.escape(str(addr.get('flat', '')))
        safe_comment = html.escape(str(addr.get('comment', '')))

        # 2. ФОРМАТИРОВАНИЕ АДРЕСА
        addr_parts = []
        if safe_street: addr_parts.append(f"ул. {safe_street}")
        if safe_house: addr_parts.append(f"д. {safe_house}")
        if safe_entrance: addr_parts.append(f"под. {safe_entrance}")
        if safe_floor: addr_parts.append(f"эт. {safe_floor}")
        if safe_flat: addr_parts.append(f"кв. {safe_flat}")
        
        address_text = ", ".join(addr_parts) if addr_parts else "Не указан"
        if safe_comment: 
            address_text += f"\n<b>Коммент:</b> <i>{safe_comment}</i>"

        # 3. ФОРМАТИРОВАНИЕ КОРЗИНЫ
        items_lines = []
        if isinstance(cart_items, list):
            for item in cart_items:
                safe_item_name = html.escape(str(item.get('name', 'Десерт')))
                qty = item.get('quantity', 1)
                items_lines.append(f"• {safe_item_name} — {qty} шт.")
        items_text = "\n".join(items_lines) if items_lines else "Пусто"

        # 4. ЛОГИКА ОТОБРАЖЕНИЯ КЛИЕНТА И КНОПКИ СВЯЗИ
        if tg_username_raw == "Не указан" or not tg_username_raw:
            client_display = f"{safe_name} (Юзернейм скрыт)"
            if tg_id:
                contact_btn = InlineKeyboardButton(text="💬 Написать клиенту", url=f"tg://user?id={tg_id}")
            else:
                clean_phone = str(phone_raw).replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
                contact_btn = InlineKeyboardButton(text="📞 Позвонить", url=f"tel:{clean_phone}")
        else:
            client_display = f"{safe_name} (@{safe_username})"
            contact_btn = InlineKeyboardButton(text="💬 Написать клиенту", url=f"https://t.me/{safe_username}")

        # ФОРМИРОВАНИЕ ТЕКСТА ДЛЯ АДМИНА
        admin_text = (
            f"🔔 <b>СОЗДАН НОВЫЙ ЗАКАЗ #{order_id}</b>\n"
            f"👤 Клиент: {client_display}\n"
            f"📱 Телефон: {safe_phone}\n"
            f"📍 Адрес: {address_text}\n"
            f"📅 Дата: {safe_date}\n"
            f"🧁 Состав:\n{items_text}\n"
            f"💰 Сумма: {total_price} ₽\n"
            f"⏳ Статус: Ожидает выбора способа оплаты клиентом"
        )

        admin_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"adm_confirm_{order_id}")],
            [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"adm_reject_{order_id}")],
            [contact_btn]
        ])

        # Сохранение заказа и статуса в памяти
        orders_db[order_id] = {
            "user_id": message.from_user.id,
            "total_price": total_price,
            "admin_text": admin_text,
            "contact_btn": contact_btn,
            "admin_msg_id": None
        }

        # МГНОВЕННАЯ отправка уведомления админу
        admin_msg = await bot.send_message(
            chat_id=ADMIN_ID, 
            text=admin_text, 
            reply_markup=admin_kb, 
            parse_mode="HTML"
        )
        orders_db[order_id]["admin_msg_id"] = admin_msg.message_id

        # Отправка карточки заказа клиенту
        client_text = (
            f"🧁 <b>Заказ #{order_id}</b>\n\n"
            f"<b>Состав:</b>\n{items_text}\n\n"
            f"💰 <b>Итого к оплате:</b> {total_price} ₽\n\n"
            f"Выберите способ оплаты 👇"
        )
        
        client_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚡️ Оплатить по СБП", callback_data=f"pay_sbp_{order_id}")],
            [InlineKeyboardButton(text="💵 Наличными курьеру", callback_data=f"pay_cash_{order_id}")]
        ])
        
        await message.answer(client_text, reply_markup=client_kb, parse_mode="HTML")

    except Exception as e:
        raw_data = getattr(message.web_app_data, 'data', 'Нет данных')
        error_text = (
            f"❌ <b>ОШИБКА В БОТЕ:</b>\n<code>{html.escape(str(e))}</code>\n\n"
            f"<b>Трейсбек:</b>\n<code>{html.escape(traceback.format_exc())}</code>\n\n"
            f"<b>Сырой JSON от фронтенда:</b>\n<code>{html.escape(str(raw_data))}</code>"
        )
        
        # Обрезаем текст до лимитов Telegram
        if len(error_text) > 4000:
            error_text = error_text[:4000] + "\n\n...[ОБРЕЗАНО]"
            
        await message.answer(error_text, parse_mode="HTML")
        if message.from_user.id != ADMIN_ID:
            await bot.send_message(chat_id=ADMIN_ID, text=error_text, parse_mode="HTML")
        return


@dp.callback_query(F.data.startswith("pay_sbp_"))
async def process_sbp_payment(callback: types.CallbackQuery):
    order_id = callback.data.replace("pay_sbp_", "")
    order_data = orders_db.get(order_id)
    
    if not order_data:
        return await callback.answer("Сессия заказа не найдена.", show_alert=True)
    
    total_price = order_data.get("total_price", 0)
    text = (
        f"💳 <b>Оплата заказа #{order_id} через СБП</b>\n\n"
        f"💰 Сумма к переводу: <b>{total_price} ₽</b>\n"
        f"📱 Номер телефона: <code>{SBP_PHONE}</code>\n"
        f"🏦 Банк: {SBP_BANK}\n"
        f"👤 Получатель: {SBP_RECEIVER}\n\n"
        f"Инструкция:\n"
        f"1. Скопируйте номер телефона и переведите {total_price} ₽ в приложении своего банка по СБП.\n"
        f"2. После перевода нажмите кнопку «✅ Я оплатил(а)» ниже."
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я оплатил(а)", callback_data=f"sbp_done_{order_id}")]
    ])
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@dp.callback_query(F.data.startswith("sbp_done_"))
async def process_sbp_done(callback: types.CallbackQuery):
    order_id = callback.data.replace("sbp_done_", "")
    order_data = orders_db.get(order_id)
    
    if not order_data:
        return await callback.answer("Сессия заказа не найдена.", show_alert=True)
        
    await callback.message.edit_text(
        "⏳ Платеж на проверке! Мы уже сверяем поступление средств. Курьер / Служба заботы свяжется с вами для подтверждения доставки ✨",
        parse_mode="HTML"
    )
    
    if order_data.get("admin_msg_id"):
        new_status = "⚠️ Клиент заявил об оплате по СБП! Проверьте выписку банка"
        new_text = order_data["admin_text"].replace(
            "⏳ Статус: Ожидает выбора способа оплаты клиентом", 
            f"⏳ Статус: {new_status}"
        )
        orders_db[order_id]["admin_text"] = new_text
        
        admin_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"adm_confirm_{order_id}")],
            [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"adm_reject_{order_id}")],
            [order_data["contact_btn"]]
        ])
        
        try:
            await bot.edit_message_text(
                chat_id=ADMIN_ID, 
                message_id=order_data["admin_msg_id"], 
                text=new_text, 
                reply_markup=admin_kb, 
                parse_mode="HTML"
            )
        except Exception as e:
            logging.error(f"Ошибка обновления сообщения админа: {e}", exc_info=True)
            
    await callback.answer()


@dp.callback_query(F.data.startswith("pay_cash_"))
async def process_cash_payment(callback: types.CallbackQuery):
    order_id = callback.data.replace("pay_cash_", "")
    order_data = orders_db.get(order_id)
    
    if not order_data:
        return await callback.answer("Сессия заказа не найдена.", show_alert=True)
        
    await callback.message.edit_text(
        "Заказ принят с оплатой при получении! Курьер / Служба заботы свяжется с вами для подтверждения доставки ✨",
        parse_mode="HTML"
    )
    
    if order_data.get("admin_msg_id"):
        new_status = "💵 Оплата наличными при получении"
        new_text = order_data["admin_text"].replace(
            "⏳ Статус: Ожидает выбора способа оплаты клиентом", 
            f"⏳ Статус: {new_status}"
        )
        orders_db[order_id]["admin_text"] = new_text
        
        admin_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"adm_confirm_{order_id}")],
            [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"adm_reject_{order_id}")],
            [order_data["contact_btn"]]
        ])
        
        try:
            await bot.edit_message_text(
                chat_id=ADMIN_ID, 
                message_id=order_data["admin_msg_id"], 
                text=new_text, 
                reply_markup=admin_kb, 
                parse_mode="HTML"
            )
        except Exception as e:
            logging.error(f"Ошибка обновления сообщения админа: {e}", exc_info=True)
            
    await callback.answer()


@dp.callback_query(F.data.startswith("adm_confirm_"))
async def admin_confirm(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return await callback.answer("У вас нет прав для выполнения этого действия.", show_alert=True)
        
    order_id = callback.data.replace("adm_confirm_", "")
    order_data = orders_db.get(order_id)
    
    await callback.message.edit_text(f"✅ <b>ЗАКАЗ #{order_id} УСПЕШНО ПОДТВЕРЖДЕН</b>", parse_mode="HTML")
    
    if order_data:
        try:
            await bot.send_message(
                chat_id=order_data.get("user_id"), 
                text=f"🎉 Оплата подтверждена! Ваш заказ #{order_id} принят в работу, десерты приедут в субботу ✨",
                parse_mode="HTML"
            )
        except Exception as e:
            logging.error(f"Не удалось отправить уведомление клиенту: {e}", exc_info=True)
            
    await callback.answer()


@dp.callback_query(F.data.startswith("adm_reject_"))
async def admin_reject(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return await callback.answer("У вас нет прав для выполнения этого действия.", show_alert=True)
        
    order_id = callback.data.replace("adm_reject_", "")
    order_data = orders_db.get(order_id)
    
    await callback.message.edit_text(f"❌ <b>ЗАКАЗ #{order_id} ОТКЛОНЕН</b>", parse_mode="HTML")
    
    if order_data:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Поддержка 💬", url=SUPPORT_LINK)]
        ])
        try:
            await bot.send_message(
                chat_id=order_data.get("user_id"), 
                text=f"⚠️ Не удалось подтвердить оплату по заказу #{order_id}. Пожалуйста, напишите в поддержку.",
                reply_markup=kb,
                parse_mode="HTML"
            )
        except Exception as e:
            logging.error(f"Не удалось отправить уведомление клиенту: {e}", exc_info=True)
            
    await callback.answer()


async def main():
    logging.info("Бот SweetSpot запущен. Сверхбезопасный HTML-парсинг и полная отладка активны.")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())