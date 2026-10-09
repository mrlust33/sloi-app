import asyncio
import json
import uuid
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, LabeledPrice, PreCheckoutQuery

# Конфигурация (все твои токены и ID сохранены)
BOT_TOKEN = "8765647186:AAHSxInOny0IzDz5gRf83AX3wlszTRFgoXs"
PROVIDER_TOKEN = "PROVIDER_TOKEN"  # Сюда позже вставим рабочий токен ЮKassa под СБП
ADMIN_ID = 5293518524
SUPPORT_LINK = "https://t.me"
WEB_APP_URL = "https://github.io"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Временная in-memory БД для хранения структуры заказов
ORDERS_DB = {}

@dp.message(CommandStart())
async def command_start_handler(message: types.Message):
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Открыть меню 🧁", web_app=WebAppInfo(url=WEB_APP_URL))],
        [InlineKeyboardButton(text="Уточнить детали / Поддержка 💬", url=SUPPORT_LINK)]
    ])
    
    await message.answer(
        "Доставка крафтовых десертов в ЖК Жулебино Парк. Ближайшая доставка: Суббота.",
        reply_markup=markup
    )

# 1. ОБРАБОТЧИК ДАННЫХ ИЗ WEB APP: Формируем стильный чек и кнопки выбора
@dp.message(F.web_app_data)
async def web_app_data_handler(message: types.Message):
    try:
        data = json.loads(message.web_app_data.data)
        cart = data.get('cart', [])
        total_price = data.get('totalPrice', 0)
        delivery_time = data.get('delivery_time', 'Не указано')
        address = data.get('address', {})
        phone = data.get('phone', 'Не указан')
        
        # Генерируем короткий ID заказа и сохраняем JSON в память
        order_id = str(uuid.uuid4())[:8]
        ORDERS_DB[order_id] = data
        
        # Формируем состав заказа списком для красивого чека
        items_text = "\n".join([f"• {item['name']} ({item['quantity']} шт.)" for item in cart])
        
        # Собираем красивую строку адреса
        address_text = f"ул. {address.get('street', '')}, д. {address.get('house', '')}"
        if address.get('entrance'): address_text += f", под. {address['entrance']}"
        if address.get('floor'): address_text += f", эт. {address['floor']}"
        if address.get('flat'): address_text += f", кв. {address['flat']}"
        
        # Текстовый чек точь-в-точь по твоему макету
        receipt_text = (
            f"🧁 **Заказ #{order_id} оформлен!**\n\n"
            f"**Состав:**\n{items_text}\n\n"
            f"**Доставка:** {delivery_time}\n"
            f"**Адрес:** {address_text}\n"
            f"**Телефон:** `{phone}`\n\n"
            f"💰 **Итого к оплате:** {total_price} ₽\n\n"
            f"Выбери удобный способ оплаты ниже 👇"
        )
        
        # Кнопки под сообщением: Наличные или СБП
        payment_kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="💵 Наличными при получении", callback_data=f"cash_{order_id}")
            ],
            [
                InlineKeyboardButton(text="💳 Оплатить по СБП", callback_data=f"sbp_{order_id}")
            ]
        ])
        
        # Отправляем чек покупателю
        await message.answer(receipt_text, reply_markup=payment_kb, parse_mode="Markdown")
        
    except Exception as e:
        await message.answer("❌ Произошла ошибка при формировании заказа. Пожалуйста, свяжитесь с поддержкой.")

# 2. ОБРАБОТКА ВЫБОРА: НАЛИЧНЫЕ
@dp.callback_query(F.data.startswith("cash_"))
async def process_cash_payment(callback: types.CallbackQuery):
    order_id = callback.data.split("_")[1]
    data = ORDERS_DB.get(order_id, {})
    
    if not data:
        await callback.message.edit_text("❌ Сессия заказа истекла. Оформи заново в меню.")
        return
        
    # Обновляем сообщение у клиента
    await callback.message.edit_text(
        callback.message.text + "\n\n✅ **Способ оплаты:** Наличными при получении.\n"
        "Наш кондитер уже связывается с вами для подтверждения заказа! ✨",
        parse_mode="Markdown"
    )
    
    # Отправляем уведомление администратору/кондитеру в личку
    await send_admin_alert(order_id, data, "💵 НАЛИЧНЫМИ ПРИ ПОЛУЧЕНИИ")
    await callback.answer()

# 3. ОБРАБОТКА ВЫБОРА: СБП (Через нативный Telegram Invoice)
@dp.callback_query(F.data.startswith("sbp_"))
async def process_sbp_payment(callback: types.CallbackQuery):
    order_id = callback.data.split("_")[1]
    data = ORDERS_DB.get(order_id, {})
    
    if not data:
        await callback.message.edit_text("❌ Сессия заказа истекла. Оформи заново в меню.")
        return

    cart = data.get('cart', [])
    total_price = data.get('totalPrice', 0)
    
    items_text = ", ".join([f"{item['name']} x{item['quantity']}" for item in cart])
    description = f"Премиальные трайфлы: {items_text}"
    prices = [LabeledPrice(label="Сумма заказа", amount=int(total_price * 100))]
    
    # Сразу удаляем старый чек с кнопками, чтобы выставить счет
    await callback.message.delete()
    
    # Выставляем счет (при подключении ЮKassa с СБП тут автоматически появится кнопка СБП)
    await bot.send_invoice(
        chat_id=callback.message.chat.id,
        title="Оплата заказа по СБП в SweetSpot",
        description=description,
        payload=order_id,
        provider_token=PROVIDER_TOKEN,
        currency="RUB",
        prices=prices,
        start_parameter="sweetspot_order",
        need_name=False,
        need_phone_number=False,
        need_email=False,
        need_shipping_address=False
    )
    await callback.answer()

# Обязательный шаг для Telegram инвойсов
@dp.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

# 4. ОБРАБОТЧИК УСПЕШНОГО ПЛАТЕЖА ПО СБП
@dp.message(F.successful_payment)
async def successful_payment_handler(message: types.Message):
    order_id = message.successful_payment.invoice_payload
    data = ORDERS_DB.get(order_id, {})
    
    if not data:
        await message.answer("Оплата прошла успешно, но данные сессии потеряны. Свяжитесь с поддержкой.")
        return

    cart = data.get('cart', [])
    total_price = data.get('totalPrice', 0)
    
    items_text = "\n".join([f"- {item['name']} x{item['quantity']}" for item in cart])
    
    # Подтверждение клиенту
    await message.answer(
        f"🎉 **Оплата успешно получена по СБП!** Спасибо за заказ.\n\n"
        f"**Состав:**\n{items_text}\n\n"
        f"**Сумма:** {total_price} ₽\n"
        f"Скоро кондитер свяжется с вами!"
    )
    
    # Уведомление админу
    await send_admin_alert(order_id, data, "💳 ОПЛАЧЕНО ПО СБП")
    
    # Чистим кэш
    if order_id in ORDERS_DB:
        del ORDERS_DB[order_id]

# Вспомогательная функция отправки карточки админу
async def send_admin_alert(order_id, data, method_name):
    cart = data.get('cart', [])
    address = data.get('address', {})
    total_price = data.get('totalPrice', 0)
    delivery_time = data.get('delivery_time', 'Не указано')
    phone = data.get('phone', 'Не указан')
    tg_username = data.get('tg_username', 'Скрыт')
    
    items_text = "\n".join([f"- {item['name']} x{item['quantity']}" for item in cart])
    address_text = (
        f"Ул. {address.get('street')}, д. {address.get('house')}, "
        f"под. {address.get('entrance', '-')}, эт. {address.get('floor', '-')}, кв. {address.get('flat', '-')}"
    )
    comment = address.get('comment', 'Нет')

    admin_alert = (
        f"🚨 **НОВЫЙ ЗАКАЗ #{order_id}**\n"
        f"**Способ оплаты:** {method_name}\n"
        f"**Клиент:** @{tg_username} | {phone}\n\n"
        f"**Заказ:**\n{items_text}\n"
        f"**Сумма:** {total_price} ₽\n\n"
        f"**Время доставки:** {delivery_time}\n"
        f"**Адрес:** {address_text}\n"
        f"**Комментарий:** {comment}"
    )
    await bot.send_message(chat_id=ADMIN_ID, text=admin_alert)

async def main():
    print("Бот SweetSpot успешно запущен с поддержкой Наличных и СБП!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
