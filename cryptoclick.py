import os
import sqlite3
import time
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Создаем соединение с базой данных
conn = sqlite3.connect("game.db")
cur = conn.cursor()

# Создаем таблицу, если не существует
cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    coins INTEGER DEFAULT 0,
    power INTEGER DEFAULT 1,
    passive INTEGER DEFAULT 0,
    last_bonus INTEGER DEFAULT 0
)
""")
conn.commit()

# Получаем или создаем пользователя
def get_user(user_id):
    user = cur.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
    if not user:
        cur.execute("INSERT INTO users VALUES (?, 0, 1, 0, 0)", (user_id,))
        conn.commit()
        user = cur.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
    return user

# Создаем меню
def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(text="⛏ Майнить", callback_data="click")],
        [InlineKeyboardButton(text="🎁 Бонус", callback_data="bonus")],
        [InlineKeyboardButton(text="🛒 Магазин", callback_data="shop")],
        [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")],
        [InlineKeyboardButton(text="🏆 ТОП", callback_data="top")]
    ])

# Стартовая команда
async def start(update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    get_user(user_id)
    await update.message.reply_text("🎮 Добро пожаловать в CryptoClick!", reply_markup=menu())

# Обработка нажатий
async def callback_query(update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    user = get_user(user_id)

    if data == "click":
        coins = user[1] + user[2]
        cur.execute("UPDATE users SET coins=? WHERE user_id=?", (coins, user_id))
        conn.commit()
        await query.edit_message_text(
            f"⛏ +{user[2]} монет\n💰 Баланс: {coins}",
            reply_markup=menu()
        )

    elif data == "bonus":
        now = int(time.time())
        last_bonus = user[4]
        if now - last_bonus >= 86400:
            reward = 100 + user[2] * 10
            new_coins = user[1] + reward
            cur.execute("UPDATE users SET coins=?, last_bonus=? WHERE user_id=?", (new_coins, now, user_id))
            conn.commit()
            await query.answer(f"🎁 Ты получил {reward} монет!")
        else:
            remaining = 86400 - (now - last_bonus)
            hours = remaining // 3600
            await query.answer(f"❌ Бонус через {hours} часов")
        await query.edit_message_text("🎁 Бонус", reply_markup=menu())

    elif data == "profile":
        await query.edit_message_text(
            f"👤 Профиль\n\n"
            f"Монеты: {user[1]}\n"
            f"Сила: {user[2]}\n"
            f"Пассив: {user[3]}\n",
            reply_markup=menu()
        )

def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(callback_query))

    # Запуск бота
    application.run_polling()

# Запуск
if __name__ == "__main__":
    main()