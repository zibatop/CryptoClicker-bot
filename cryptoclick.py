import asyncio
import sqlite3
import os
import time
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

#БАЗА
conn = sqlite3.connect("game.db")
cur = conn.cursor()
cur.execute("""
CREATE TABLE IF NOT EXISTS users(
    user_id INTEGER PRIMARY KEY,
    coins INTEGER,
    power INTEGER,
    passive INTEGER,
    last_bonus INTEGER
)
""")
conn.commit()

def get_user(user_id):
    user = cur.execute(
        "SELECT * FROM users WHERE user_id=?",
        (user_id,)
    ).fetchone()

    if not user:
        cur.execute(
            "INSERT INTO users VALUES(?,?,?,?,?)",
            (user_id, 0, 1, 0, 0)
        )
        conn.commit()
        user = (user_id, 0, 1, 0, 0)

    return user

#МЕНЮ
def menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⛏ Майнить", callback_data="click")],
        [InlineKeyboardButton(text="🎁 Бонус", callback_data="bonus")],
        [InlineKeyboardButton(text="🛒 Магазин", callback_data="shop")],
        [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")],
        [InlineKeyboardButton(text="🏆 ТОП", callback_data="top")]
    ])

#СТАРТ
@dp.message(CommandStart())
async def start(msg: types.Message):
    get_user(msg.from_user.id)
    await msg.answer("🎮 Добро пожаловать в CryptoClick", reply_markup=menu())

#КЛИК
@dp.callback_query(F.data == "click")
async def click(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    coins = user[1] + user[2]
    cur.execute(
        "UPDATE users SET coins=? WHERE user_id=?",
        (coins, call.from_user.id)
    )
    conn.commit()
    await call.message.edit_text(
        f"⛏ +{user[2]} монет\n💰 Баланс: {coins}",
        reply_markup=menu()
    )

#БОНУС
@dp.callback_query(F.data == "bonus")
async def bonus(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    now = int(time.time())
    if now - user[4] >= 86400:
        reward = 100 + user[2] * 10
        cur.execute(
            "UPDATE users SET coins=?, last_bonus=? WHERE user_id=?",
            (user[1] + reward, now, call.from_user.id)
        )
        conn.commit()
        await call.answer(f"🎁 Ты получил {reward} монет")
    else:
        left = 86400 - (now - user[4])
        hours = left // 3600
        await call.answer(f"❌ Бонус через {hours} ч")
    await call.message.edit_text("🎁 Бонус", reply_markup=menu())

#ПРОФИЛЬ
@dp.callback_query(F.data == "profile")
async def profile(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    await call.message.edit_text(
        f"👤 Профиль\n\n"
        f"💰 Монеты: {user[1]}\n"
        f"⚡ Клик: {user[2]}\n"
        f"🤖 Роботы: {user[3]}",
        reply_markup=menu()
    )

#МАГАЗИН 
@dp.callback_query(F.data == "shop")
async def shop(call: types.CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💻 +1 клик (50)", callback_data="buy_power")],
        [InlineKeyboardButton(text="🤖 Робот +1/10сек (200)", callback_data="buy_robot")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
    ])
    await call.message.edit_text("🛒 Магазин", reply_markup=kb)

@dp.callback_query(F.data == "buy_power")
async def buy_power(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    if user[1] >= 50:
        cur.execute(
            "UPDATE users SET coins=?, power=? WHERE user_id=?",
            (user[1]-50, user[2]+1, call.from_user.id)
        )
        conn.commit()
        await call.answer("✅ Куплено")
    else:
        await call.answer("❌ Не хватает")
    await shop(call)

@dp.callback_query(F.data == "buy_robot")
async def buy_robot(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    if user[1] >= 200:
        cur.execute(
            "UPDATE users SET coins=?, passive=? WHERE user_id=?",
            (user[1]-200, user[3]+1, call.from_user.id)
        )
        conn.commit()
        await call.answer("🤖 Робот куплен")
    else:
        await call.answer("❌ Не хватает")
    await shop(call)

#ТОП
@dp.callback_query(F.data == "top")
async def top(call: types.CallbackQuery):
    users = cur.execute(
        "SELECT user_id, coins FROM users ORDER BY coins DESC LIMIT 10"
    ).fetchall()
    text = "🏆 ТОП игроков\n\n"
    i = 1
    for u in users:
        try:
            name = (await bot.get_chat(u[0])).first_name
        except:
            name = "Игрок"

        text += f"{i}. {name} — {u[1]} 💰\n"
        i += 1
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
    ])
    await call.message.edit_text(text, reply_markup=kb)

#НАЗАД
@dp.callback_query(F.data == "back")
async def back(call: types.CallbackQuery):
    await call.message.edit_text("🎮 Меню", reply_markup=menu())

#АВТОДОХОД 
async def passive_income():
    while True:
        users = cur.execute(
            "SELECT user_id, passive FROM users"
        ).fetchall()
        for u in users:
            if u[1] > 0:
                cur.execute(
                    "UPDATE users SET coins = coins + ? WHERE user_id=?",
                    (u[1], u[0])
                )
        conn.commit()
        await asyncio.sleep(10)
async def main():
    asyncio.create_task(passive_income())
    await dp.start_polling(bot)
asyncio.run(main())