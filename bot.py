import asyncio
import json
import uuid
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton, 
    ReplyKeyboardMarkup, KeyboardButton, 
    WebAppInfo
)

# Конфигурация проекта SweetSpot (СТРОГО БЕЗ ПРОБЕЛОВ В НАЧАЛЕ СТРОК)
BOT_TOKEN = "8765647186:AAHSxInOny0IzDz5gRf83AX3wlszTRFgoXs"
ADMIN_ID = 5293518524
SUPPORT_LINK = "https://t.me"
WEB_APP_URL = "https://mrlust33.github.io/sloi-app/?v=6.0"

# Реквизиты для перевода СБП
SBP_PHONE = "+7 (977) 627-44-42"
SBP_BANK = "Т-Банк / Сбербанк"
SBP_RECEIVER = "Андрей А."

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Временная in-memory БД для хранения структуры заказов
ORDERS_DB = {}

@dp.message(CommandStart())
async def command_start_handler(message: types.Message):
    # Нижняя Reply-клавиатура (гарантирует 100% срабатывание sendData)
    reply_kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Открыть меню 🧁", web_app=WebAppInfo(url=WEB_APP_URL))]],
        resize_keyboard=True
    )
    
    # Инлайн-клавиатура для поддержки
    inline_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Уточнить детали / Поддержка 💬", url=SUPPORT_LINK)]
    ])
    
    await message.answer("Главное меню закреплено внизу экрана 👇", reply_markup=reply_kb)
    await message.answer(
        "SweetSpot | Доставка десертов\n"
        "Премиальные трайфлы ручной работы. Доставляем свежие партии по субботам ✨",
        reply_markup=inline_kb
    )

# 1. ОБРАБОТЧИК ДАННЫХ ИЗ WEB APP
@dp.message(F.web_app_data)
async def web_app_data_handler(message: types.Message):
    print(f"Получены данные заказа: {message.web_app_data.data}")
    try:
        data = json.loads(message.web_app_data.data)
        # Генерация ID без дефисов (надежно для callback_data)
        order_id = uuid.uuid4().hex[:8].upper()
        ORDERS_DB[order_id] = data
        
        await show_payment_options(message, order_id, data)
    except Exception as e:
        await message.answer("❌ Произошла ошибка при обработке заказа. Обратитесь в поддержку.")

async def show_payment_options(target, order_id, data):
    cart = data.get('cart', [])
    total_price = data.get('totalPrice', 0)
    delivery_time = data.get('delivery_time', 'Не указано')
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
        f"**Доставка:** {delivery_time}\n"
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

# КНОПКА "НАЗАД" В МЕНЮ ВЫБОРА ОПЛАТЫ
@dp.callback_query(F.data.startswith("back_pay_"))
async def back_to_payment(callback: types.CallbackQuery):
    order_id = callback.data.replace("back_pay_", "")
    data = ORDERS_DB.get(order_id)
    
    if not data:
        await callback.message.edit_text("❌ Сессия заказа истекла. Оформи заново в меню.")
        return await callback.answer()
        
    await show_payment_options(callback, order_id, data)
    await callback.answer()

# 2. СЦЕНАРИЙ: ОПЛАТИТЬ ПО СБП (РУЧНОЙ ПЕРЕВОД)
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

# УСПЕШНАЯ ОПЛАТА СБП (ПОДТВЕРЖДЕНИЕ КЛИЕНТОМ)
@dp.callback_query(F.data.startswith("sbp_done_"))
async def sbp_done_handler(callback: types.CallbackQuery):
    order_id = callback.data.replace("sbp_done_", "")
    data = ORDERS_DB.get(order_id)
    
    if not data:
        await callback.message.edit_text("❌ Сессия заказа истекла. Оформи заново в меню.")
        return await callback.answer()

    await callback.message.edit_text(
        "⏳ **Платеж на проверке!** Кондитер уже сверяет поступление средств по выписке банка. "
        "Скоро свяжемся с вами в личных сообщениях! ✨",
        parse_mode="Markdown"
    )
    
    await send_admin_alert(order_id, data, "[⚡️ ОПЛАЧЕНО ПО СБП (ПРОВЕРИТЬ БАНК)]")
    del ORDERS_DB[order_id]
    await callback.answer()

# 3. СЦЕНАРИЙ: НАЛИЧНЫМИ КУРЬЕРУ
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
        f"Наш кондитер скоро свяжется с вами для уточнения деталей! ✨",
        parse_mode="Markdown"
    )
    
    await send_admin_alert(order_id, data, "[💵 НАЛИЧНЫМИ КУРЬЕРУ]")
    del ORDERS_DB[order_id]
    await callback.answer()

# ОТПРАВКА УВЕДОМЛЕНИЯ АДМИНУ
async def send_admin_alert(order_id, data, tag):
    cart = data.get('cart', [])
    address = data.get('address', {})
    total_price = data.get('totalPrice', 0)
    delivery_time = data.get('delivery_time', 'Не указано')
    phone = data.get('phone', 'Не указан')
    tg_username = data.get('tg_username', 'Скрыт')
    
    items_text = "\n".join([f"- {item['name']} x{item['quantity']}" for item in cart])
    address_text = (
        f"ул. {address.get('street')}, д. {address.get('house')}, "
        f"под. {address.get('entrance', '-')}, эт. {address.get('floor', '-')}, кв. {address.get('flat', '-')}"
    )
    comment = address.get('comment', 'Нет')

    admin_alert = (
        f"{tag}\n"
        f"🚨 **Заказ #{order_id}**\n"
        f"**Клиент:** @{tg_username} | `{phone}`\n\n"
        f"**Состав:**\n{items_text}\n"
        f"**Сумма:** {total_price} ₽\n\n"
        f"**Время:** {delivery_time}\n"
        f"**Адрес:** {address_text}\n"
        f"**Комментарий:** {comment}"
    )
    await bot.send_message(chat_id=ADMIN_ID, text=admin_alert, parse_mode="Markdown")

async def main():
    print("Бот SweetSpot запущен! Ручной СБП-терминал активирован.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())