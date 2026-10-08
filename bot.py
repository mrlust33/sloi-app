import asyncio
import json
import uuid
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, LabeledPrice, PreCheckoutQuery

# Конфигурация
BOT_TOKEN = "8765647186:AAHSxInOny0IzDz5gRf83AX3wlszTRFgoXs"
PROVIDER_TOKEN = "PROVIDER_TOKEN"  # Вставь сюда TEST-токен от @BotFather (например ЮKassa)
ADMIN_ID = 5293518524
SUPPORT_LINK = "https://t.me/M_be4"
WEB_APP_URL = "https://mrlust33.github.io/sloi-app/?v=5"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Временная in-memory БД, чтобы обойти ограничение Telegram в 128 байт для payload инвойса
ORDERS_DB = {}

@dp.message(CommandStart())
async def command_start_handler(message: types.Message):
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Открыть меню", web_app=WebAppInfo(url=WEB_APP_URL))],
        [InlineKeyboardButton(text="Уточнить детали / Поддержка", url=SUPPORT_LINK)]
    ])
    
    await message.answer(
        "Доставка крафтовых десертов в ЖК Жулебино Парк. Ближайшая доставка: Суббота.",
        reply_markup=markup
    )

# Обработчик данных, приходящих из Web App при оформлении заказа
@dp.message(F.web_app_data)
async def web_app_data_handler(message: types.Message):
    try:
        data = json.loads(message.web_app_data.data)
        cart = data.get('cart', [])
        total_price = data.get('totalPrice', 0)
        
        # Генерируем короткий ID заказа и сохраняем JSON в память
        order_id = str(uuid.uuid4())[:8]
        ORDERS_DB[order_id] = data
        
        # Формируем описание для счета
        items_text = ", ".join([f"{item['name']} x{item['quantity']}" for item in cart])
        description = f"Премиальные трайфлы: {items_text}"
        
        # Цена указывается в копейках (умножаем на 100)
        prices = [LabeledPrice(label="Сумма заказа", amount=int(total_price * 100))]
        
        # Выставляем счет
        await bot.send_invoice(
            chat_id=message.chat.id,
            title="Оплата заказа в SweetSpot",
            description=description,
            payload=order_id, # Передаем только ID, чтобы не пробить лимит в 128 байт
            provider_token=PROVIDER_TOKEN,
            currency="RUB",
            prices=prices,
            start_parameter="sweetspot_order",
            need_name=False,
            need_phone_number=False,
            need_email=False,
            need_shipping_address=False
        )
    except Exception as e:
        await message.answer("Произошла ошибка при формировании счета. Пожалуйста, свяжитесь с поддержкой.")

# Обязательный обработчик PreCheckoutQuery (мгновенно одобряем транзакцию)
@dp.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

# Обработчик успешного платежа
@dp.message(F.successful_payment)
async def successful_payment_handler(message: types.Message):
    # Достаем ID заказа из payload и вытягиваем данные из БД
    order_id = message.successful_payment.invoice_payload
    data = ORDERS_DB.get(order_id, {})
    
    if not data:
        await message.answer("Оплата прошла успешно, но данные заказа потеряны. Свяжитесь с поддержкой.")
        return

    cart = data.get('cart', [])
    address = data.get('address', {})
    total_price = data.get('totalPrice', 0)
    delivery_time = data.get('delivery_time', 'Не указано')
    phone = data.get('phone', 'Не указан')
    tg_username = data.get('tg_username', 'Скрыт')
    
    items_text = "\n".join([f"- {item['name']} x{item['quantity']}" for item in cart])
    address_text = (
        f"Ул. {address.get('street')}, д. {address.get('house')}, "
        f"под. {address.get('entrance')}, эт. {address.get('floor')}, кв. {address.get('flat')}"
    )
    comment = address.get('comment', 'Нет')
    
    # Чек клиенту
    client_receipt = (
        f"🎉 Оплата успешно прошла! Спасибо за заказ.\n\n"
        f"Состав:\n{items_text}\n\n"
        f"Сумма: {total_price} ₽\n"
        f"Время доставки: {delivery_time}\n"
        f"Адрес доставки: {address_text}"
    )
    await message.answer(client_receipt)
    
    # Уведомление администратору/кондитеру
    admin_alert = (
        f"🔥 НОВЫЙ ОПЛАЧЕННЫЙ ЗАКАЗ!\n"
        f"Клиент: @{tg_username} | {phone}\n\n"
        f"Заказ:\n{items_text}\nСумма: {total_price} ₽\n\n"
        f"Время доставки: {delivery_time}\n"
        f"Адрес: {address_text}\n"
        f"Комментарий: {comment}"
    )
    await bot.send_message(chat_id=ADMIN_ID, text=admin_alert)
    
    # Подчищаем память после успешной обработки
    del ORDERS_DB[order_id]

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())