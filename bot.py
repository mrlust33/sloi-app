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

# ЖЕСТКИЕ КОНСТАНТЫ ПРОЕКТА
BOT_TOKEN = "8765647186:AAGez9_BPRed47X2tp-QBc9MVERmxrOUkqk"
ADMIN_ID = 5293518524
SUPPORT_LINK = "tg://user?id=5293518524"
WEB_APP_URL = "https://github.io"

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
    await message.answer(text, reply_markup=reply_kb)
    await message.answer("Для связи с нами используйте кнопку ниже:", reply_markup=inline_kb)


@dp.message(F.web_app_data)
async def web_app_data_handler(message: types.Message):
    try:
        data = json.loads(message.web_app_data.data)
        order_id = uuid.uuid4().hex[:8].upper()
        tg_user = message.from_user
        
        cart = data.get('cart', [])
        total_price = data.get('totalPrice', 0)
        delivery_date = data.get('delivery_date', data.get('delivery_time', 'Не указано'))
        address_info = data.get('address', {})
        phone = data.get('phone', 'Не указан')

        items_text = "\n".join([f"- {item['name']} x{item['quantity']}" for item in cart])
        address_text = f"ул. {address_info.get('street', '')}, д. {address_info.get('house', '')}"
        if address_info.get('entrance'): address_text += f", под. {address_info.get('entrance')}"
        if address_info.get('floor'): address_text += f", эт. {address_info.get('floor')}"
        if address_info.get('flat'): address_text += f", кв. {address_info.get('flat')}"

        # Логика для контактных данных и выделения жирным шрифтом
        if tg_user.username:
            client_text = f"{tg_user.full_name} (@{tg_user.username})"
            phone_text = phone
            contact_url = f"https://t.me/{tg_user.username}"
        else:
            client_text = f"**{tg_user.full_name}**"
            phone_text = f"**{phone}**"
            contact_url = f"tg://user?id={tg_user.id}"

        admin_text = (
            f"🔔 СОЗДАН НОВЫЙ ЗАКАЗ #{order_id}\n"
            f"👤 Клиент: {client_text}\n"
            f"📱 Телефон: {phone_text}\n"
            f"📍 Адрес: {address_text}\n"
            f"📅 Дата: {delivery_date}\n"
            f"🧁 Состав:\n{items_text}\n"
            f"💰 Сумма: {total_price} ₽\n"
            f"⏳ Статус: Ожидает выбора способа оплаты клиентом"
        )

        # Сохранение заказа и статуса в памяти
        orders_db[order_id] = {
            "user_id": tg_user.id,
            "username": tg_user.username,
            "full_name": tg_user.full_name,
            "total_price": total_price,
            "admin_text": admin_text,
            "contact_url": contact_url,
            "admin_msg_id": None
        }

        admin_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"adm_confirm_{order_id}")],
            [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"adm_reject_{order_id}")],
            [InlineKeyboardButton(text="💬 Написать клиенту", url=contact_url)]
        ])

        # МГНОВЕННАЯ отправка уведомления админу
        admin_msg = await bot.send_message(chat_id=ADMIN_ID, text=admin_text, reply_markup=admin_kb, parse_mode="Markdown")
        orders_db[order_id]["admin_msg_id"] = admin_msg.message_id

        # Отправка карточки заказа клиенту
        client_text = (
            f"🧁 **Заказ #{order_id}**\n\n"
            f"**Состав:**\n{items_text}\n\n"
            f"💰 **Сумма:** {total_price} ₽\n\n"
            f"Выберите способ оплаты 👇"
        )
        
        client_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚡️ Оплатить по СБП", callback_data=f"pay_sbp_{order_id}")],
            [InlineKeyboardButton(text="💵 Наличными при получении", callback_data=f"pay_cash_{order_id}")]
        ])
        
        await message.answer(client_text, reply_markup=client_kb, parse_mode="Markdown")

    except Exception as e:
        print(f"Ошибка при обработке заказа: {e}")
        await message.answer("❌ Произошла ошибка при формировании заказа. Пожалуйста, обратитесь в поддержку.")


@dp.callback_query(F.data.startswith("pay_sbp_"))
async def process_sbp_payment(callback: types.CallbackQuery):
    order_id = callback.data.replace("pay_sbp_", "")
    order_data = orders_db.get(order_id)
    
    if not order_data:
        return await callback.answer("Сессия заказа не найдена.", show_alert=True)
    
    total_price = order_data["total_price"]
    text = (
        f"💳 **Оплата заказа #{order_id} через СБП**\n\n"
        f"💰 Сумма к переводу: {total_price} ₽\n"
        f"📱 Номер телефона: `{SBP_PHONE}` (нажмите, чтобы скопировать)\n"
        f"🏦 Банк: {SBP_BANK}\n"
        f"👤 Получатель: {SBP_RECEIVER}\n\n"
        f"Инструкция:\n"
        f"1. Скопируйте номер телефона и переведите {total_price} ₽ в приложении своего банка по СБП.\n"
        f"2. После перевода нажмите кнопку «✅ Я оплатил(а)» ниже. Кондитер сверит поступление и подтвердит заказ! ✨"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я оплатил(а)", callback_data=f"sbp_done_{order_id}")]
    ])
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()


@dp.callback_query(F.data.startswith("sbp_done_"))
async def process_sbp_done(callback: types.CallbackQuery):
    order_id = callback.data.replace("sbp_done_", "")
    order_data = orders_db.get(order_id)
    
    if not order_data:
        return await callback.answer("Сессия заказа не найдена.", show_alert=True)
        
    await callback.message.edit_text("⏳ Платеж на проверке! Мы уже сверяем поступление средств. Курьер / Служба заботы свяжется с вами для подтверждения доставки ✨")
    
    if order_data.get("admin_msg_id"):
        new_status = "⚠️ Клиент заявил об оплате по СБП! Проверьте выписку банка"
        new_text = order_data["admin_text"].replace("⏳ Статус: Ожидает выбора способа оплаты клиентом", f"⏳ Статус: {new_status}")
        orders_db[order_id]["admin_text"] = new_text
        
        admin_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"adm_confirm_{order_id}")],
            [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"adm_reject_{order_id}")],
            [InlineKeyboardButton(text="💬 Написать клиенту", url=order_data["contact_url"])]
        ])
        
        try:
            await bot.edit_message_text(chat_id=ADMIN_ID, message_id=order_data["admin_msg_id"], text=new_text, reply_markup=admin_kb, parse_mode="Markdown")
        except Exception as e:
            print(f"Ошибка обновления сообщения админа: {e}")
            await bot.send_message(chat_id=ADMIN_ID, text=f"Заказ #{order_id}: {new_status}")
            
    await callback.answer()


@dp.callback_query(F.data.startswith("pay_cash_"))
async def process_cash_payment(callback: types.CallbackQuery):
    order_id = callback.data.replace("pay_cash_", "")
    order_data = orders_db.get(order_id)
    
    if not order_data:
        return await callback.answer("Сессия заказа не найдена.", show_alert=True)
        
    await callback.message.edit_text("Заказ принят с оплатой при получении! Курьер свяжется с вами перед доставкой ✨")
    
    if order_data.get("admin_msg_id"):
        new_status = "💵 Способ оплаты изменен клиентом на: Наличными при получении"
        new_text = order_data["admin_text"].replace("⏳ Статус: Ожидает выбора способа оплаты клиентом", f"⏳ Статус: {new_status}")
        orders_db[order_id]["admin_text"] = new_text
        
        admin_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"adm_confirm_{order_id}")],
            [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"adm_reject_{order_id}")],
            [InlineKeyboardButton(text="💬 Написать клиенту", url=order_data["contact_url"])]
        ])
        
        try:
            await bot.edit_message_text(chat_id=ADMIN_ID, message_id=order_data["admin_msg_id"], text=new_text, reply_markup=admin_kb, parse_mode="Markdown")
        except Exception as e:
            print(f"Ошибка обновления сообщения админа: {e}")
            
    await callback.answer()


@dp.callback_query(F.data.startswith("adm_confirm_"))
async def admin_confirm(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return await callback.answer("У вас нет прав.", show_alert=True)
        
    order_id = callback.data.replace("adm_confirm_", "")
    order_data = orders_db.get(order_id)
    
    await callback.message.edit_text(f"✅ ЗАКАЗ #{order_id} УСПЕШНО ПОДТВЕРЖДЕН", parse_mode="Markdown")
    
    if order_data:
        try:
            await bot.send_message(
                chat_id=order_data["user_id"], 
                text=f"🎉 Оплата подтверждена! Ваш заказ #{order_id} принят в работу, десерты приедут в субботу ✨"
            )
        except Exception as e:
            print(f"Не удалось отправить уведомление клиенту: {e}")
            
    await callback.answer()


@dp.callback_query(F.data.startswith("adm_reject_"))
async def admin_reject(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return await callback.answer("У вас нет прав.", show_alert=True)
        
    order_id = callback.data.replace("adm_reject_", "")
    order_data = orders_db.get(order_id)
    
    await callback.message.edit_text(f"❌ ЗАКАЗ #{order_id} ОТКЛОНЕН", parse_mode="Markdown")
    
    if order_data:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Поддержка 💬", url=SUPPORT_LINK)]
        ])
        try:
            await bot.send_message(
                chat_id=order_data["user_id"], 
                text=f"⚠️ Не удалось подтвердить оплату по заказу #{order_id}. Пожалуйста, напишите в поддержку",
                reply_markup=kb
            )
        except Exception as e:
            print(f"Не удалось отправить уведомление клиенту: {e}")
            
    await callback.answer()


async def main():
    print("Бот SweetSpot запущен. Бэкенд с мгновенным откликом администратору готов к работе!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())