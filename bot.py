import asyncio
import json
import uuid
from datetime import datetime, timedelta, timezone
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton, 
    ReplyKeyboardMarkup, KeyboardButton, 
    WebAppInfo
)

# Конфигурация проекта SweetSpot (НЕ ИЗМЕНЯТЬ)
BOT_TOKEN = "8765647186:AAHSxInOny0IzDz5gRf83AX3wlszTRFgoXs"
ADMIN_ID = 5293518524
SUPPORT_LINK = "https://t.me"
WEB_APP_URL = "https://mrlust33.github.io/sloi-app/?v=6.0"
SBP_PHONE = "+7 (977) 627-44-42"
SBP_BANK = "Т-Банк / Сбербанк"
SBP_RECEIVER = "Андрей А."

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Временная in-memory БД
ORDERS_DB = {}

def get_next_delivery_saturday():
    msk_tz = timezone(timedelta(hours=3))
    now = datetime.now(msk_tz)
    days_ahead = 5 - now.weekday()
    if days_ahead < 0 or (days_ahead == 0 and now.hour >= 20):
        days_ahead += 7
    next_sat = now + timedelta(days=days_ahead)
    return next_sat.strftime("%d.%m (Суббота)")

@dp.message(CommandStart())
async def command_start_handler(message: types.Message):
    reply_kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Открыть меню 🧁", web_app=WebAppInfo(url=WEB_APP_URL))]],
        resize_keyboard=True
    )
    inline_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Уточнить детали / Поддержка 💬", url=SUPPORT_LINK)]
    ])
    
    await message.answer("Главное меню закреплено внизу экрана 👇", reply_markup=reply_kb)
    await message.answer(
        "SweetSpot | Доставка десертов\n"
        "Премиальные трайфлы ручной работы. Доставляем свежие партии по субботам ✨",
        reply_markup=inline_kb
    )

@dp.message(F.web_app_data)
async def web_app_data_handler(message: types.Message):
    print(f"Получены данные заказа: {message.web_app_data.data}")
    try:
        data = json.loads(message.web_app_data.data)
        order_id = uuid.uuid4().hex[:8].upper()
        
        tg_user = message.from_user
        username_str = f"@{tg_user.username}" if tg_user.username else f"[{tg_user.full_name}](tg://user?id={tg_user.id})"
        
        data['username_str'] = username_str
        data['user_id'] = tg_user.id
        data['calculated_saturday'] = data.get('delivery_date', get_next_delivery_saturday())
        
        ORDERS_DB[order_id] = data
        await show_payment_options(message, order_id, data)
    except Exception as e:
        print(f"Ошибка парсинга: {e}")
        await message.answer("❌ Произошла ошибка при обработке заказа. Обратитесь в поддержку.")

async def show_payment_options(target, order_id, data):
    cart = data.get('cart', [])
    total_price = data.get('totalPrice', 0)
    delivery_time = data.get('delivery_time', 'Не указано')
    calculated_sat = data.get('calculated_saturday', 'Суббота')
    address = data.get('address', {})
    phone = data.get('phone', 'Не указан')
    
    items_text = "\n".join([f"• {item['name']} ({item['quantity']} шт.)" for item in cart])
    
    address_text = f"ул. {address.get('street', '')}, д. {address.get('house', '')}"
    if address.get('entrance'): address_text += f", под. {address['entrance']}"
    if address.get('floor'): address_text += f", эт. {address['floor']}"
    if address.get('flat'): address_text += f", кв. {address['flat']}"
    
    receipt_text = (
        f"🧁 **Заказ #{order_id}**\n\n"
        f"**Состав:**\n{items_text}\n\n"
        f"**Дата доставки:** {calculated_sat}\n"
        f"**Время:** {delivery_time}\n"
        f"**Адрес:** {address_text}\n"
        f"**Телефон:** `{phone}`\n\n"
        f"💰 **Итого к оплате:** {total_price} ₽\n\n"
        f"Выберите способ оплаты 👇"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚡️ Оплатить по СБП", callback_data=f"pay_sbp_{order_id}")],
        [InlineKeyboardButton(text="💵 Наличными при получении", callback_data=f"pay_cash_{order_id}")]
    ])
    
    if isinstance(target, types.Message):
        await target.answer(receipt_text, reply_markup=kb, parse_mode="Markdown")
    else:
        await target.message.edit_text(receipt_text, reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data.startswith("back_pay_"))
async def back_to_payment(callback: types.CallbackQuery):
    order_id = callback.data.replace("back_pay_", "")
    data = ORDERS_DB.get(order_id)
    
    if not data:
        await callback.message.edit_text("❌ Сессия заказа истекла. Оформи заново в меню.")
        return await callback.answer()
        
    await show_payment_options(callback, order_id, data)
    await callback.answer()

@dp.callback_query(F.data.startswith("pay_sbp_"))
async def process_sbp_selection(callback: types.CallbackQuery):
    order_id = callback.data.replace("pay_sbp_", "")
    data = ORDERS_DB.get(order_id)
    
    if not data:
        await callback.message.edit_text("❌ Сессия заказа истекла. Оформи заново в меню.")
        return await callback.answer()

    total_price = data.get('totalPrice', 0)
    text = (
        f"💳 **Оплата заказа #{order_id} через СБП**\n\n"
        f"💰 **Сумма к переводу:** {total_price} ₽\n"
        f"📱 **Номер телефона:** `{SBP_PHONE}` (нажмите, чтобы скопировать)\n"
        f"🏦 **Банк:** {SBP_BANK}\n"
        f"👤 **Получатель:** {SBP_RECEIVER}\n\n"
        f"**Инструкция:**\n"
        f"1. Скопируйте номер телефона и переведите {total_price} ₽ в приложении своего банка по СБП.\n"
        f"2. После перевода нажмите кнопку «✅ Я оплатил(а)» ниже. Кондитер сверит поступление и подтвердит заказ! ✨"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я оплатил(а)", callback_data=f"sbp_done_{order_id}")],
        [InlineKeyboardButton(text="« Назад к способам", callback_data=f"back_pay_{order_id}")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data.startswith("sbp_done_"))
async def sbp_done_handler(callback: types.CallbackQuery):
    order_id = callback.data.replace("sbp_done_", "")
    data = ORDERS_DB.get(order_id)
    
    if not data:
        await callback.message.edit_text("❌ Сессия заказа истекла. Оформи заново в меню.")
        return await callback.answer()

    await callback.message.edit_text(
        "⏳ **Платеж на проверке!** Кондитер уже сверяет поступление средств по выписке банка. "
        "Курьер / Служба заботы свяжется с вами для подтверждения доставки! ✨",
        parse_mode="Markdown"
    )
    
    await send_admin_alert(order_id, data, "[⚡️ ОПЛАЧЕНО ПО СБП (ПРОВЕРИТЬ БАНК)]")
    del ORDERS_DB[order_id]
    await callback.answer()

@dp.callback_query(F.data.startswith("pay_cash_"))
async def process_cash_payment(callback: types.CallbackQuery):
    order_id = callback.data.replace("pay_cash_", "")
    data = ORDERS_DB.get(order_id)
    
    if not data:
        await callback.message.edit_text("❌ Сессия заказа истекла. Оформи заново в меню.")
        return await callback.answer()
        
    await callback.message.edit_text(
        f"✅ **Заказ #{order_id} подтвержден!**\n\n"
        f"Способ оплаты: **Наличными при получении**.\n"
        f"Курьер / Служба заботы свяжется с вами для подтверждения доставки! ✨",
        parse_mode="Markdown"
    )
    
    await send_admin_alert(order_id, data, "[💵 НАЛИЧНЫМИ КУРЬЕРУ]")
    del ORDERS_DB[order_id]
    await callback.answer()

async def send_admin_alert(order_id, data, tag):
    cart = data.get('cart', [])
    address = data.get('address', {})
    total_price = data.get('totalPrice', 0)
    delivery_time = data.get('delivery_time', 'Не указано')
    calculated_sat = data.get('calculated_saturday', 'Суббота')
    phone = data.get('phone', 'Не указан')
    
    username_str = data.get('username_str', 'Скрыт')
    user_id = data.get('user_id', 'Неизвестен')
    
    items_text = "\n".join([f"- {item['name']} x{item['quantity']}" for item in cart])
    address_text = (
        f"ул. {address.get('street')}, д. {address.get('house')}, "
        f"под. {address.get('entrance', '-')}, эт. {address.get('floor', '-')}, кв. {address.get('flat', '-')}"
    )
    comment = address.get('comment', 'Нет')

    admin_alert = (
        f"{tag}\n"
        f"🚨 **Заказ #{order_id}**\n"
        f"**Клиент:** {username_str} (ID: `{user_id}`)\n"
        f"**Телефон:** `{phone}`\n\n"
        f"**Состав:**\n{items_text}\n"
        f"**Сумма:** {total_price} ₽\n\n"
        f"**Дата доставки:** {calculated_sat}\n"
        f"**Время:** {delivery_time}\n"
        f"**Адрес:** {address_text}\n"
        f"**Комментарий:** {comment}"
    )
    await bot.send_message(chat_id=ADMIN_ID, text=admin_alert, parse_mode="Markdown")

async def main():
    print("Бот SweetSpot запущен. Жесткая валидация и профили активны.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())