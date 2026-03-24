import sqlite3
import os
import time
import asyncio
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

conn = sqlite3.connect("game.db", check_same_thread=False)
cur = conn.cursor()
cur.execute("""
CREATE TABLE IF NOT EXISTS users(
    user_id INTEGER PRIMARY KEY,
    coins INTEGER,
    power INTEGER,
    passive INTEGER,
    last_bonus INTEGER,
    ref INTEGER,
    premium_until INTEGER
)
""")
conn.commit()

def get_user(user_id):
    user = cur.execute("SELECT * FROM users WHERE user_id=?",(user_id,)).fetchone()
    if not user:
        cur.execute(
            "INSERT INTO users VALUES(?,?,?,?,?,?,?)",
            (user_id, 0, 1, 0, 0, 0, 0)
        )
        conn.commit()
        user = (user_id, 0, 1, 0, 0, 0, 0)
    return user

def is_premium(user):
    return user[6] > int(time.time())

def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⛏ Майнить", callback_data="click")],
        [InlineKeyboardButton("🎁 Бонус", callback_data="bonus")],
        [InlineKeyboardButton("👥 Рефералы", callback_data="ref")],
        [InlineKeyboardButton("👤 Профиль", callback_data="profile")],
        [InlineKeyboardButton("🏆 ТОП", callback_data="top")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ref = int(context.args[0]) if context.args else 0
    user = cur.execute(
        "SELECT * FROM users WHERE user_id=?",(user_id,)).fetchone()
    if not user:
        premium = 0
        if ref != 0 and ref != user_id:
            premium = int(time.time()) + 3*86400
            cur.execute(
                "UPDATE users SET coins = coins + 500 WHERE user_id=?",(ref,))
        cur.execute("INSERT INTO users VALUES(?,?,?,?,?,?,?)",(user_id, 0, 1, 0, 0, ref, premium))
        conn.commit()
    await update.message.reply_text(
        "🎮 Добро пожаловать",
        reply_markup=menu()
    )

async def click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = get_user(query.from_user.id)
    power = user[2]
    if is_premium(user):
        power *= 2
    coins = user[1] + power
    cur.execute(
        "UPDATE users SET coins=? WHERE user_id=?",(coins, query.from_user.id))
    conn.commit()
    text = f"⛏ +{power} монет\n💰 Баланс: {coins}"
    if is_premium(user):
        text += "\n⭐ ПРЕМИУМ x2"
    await query.edit_message_text(text, reply_markup=menu())

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = get_user(query.from_user.id)
    text = (
        f"👤 Профиль\n\n"
        f"💰 Монеты: {user[1]}\n"
        f"⚡ Клик: {user[2]}\n"
        f"🤖 Роботы: {user[3]}\n"
    )
    if is_premium(user):
        days = (user[6] - int(time.time())) // 86400
        text += f"⭐ Премиум: {days} дн."
    await query.edit_message_text(text, reply_markup=menu())

async def ref(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    link = f"https://t.me/{context.bot.username}?start={user_id}"
    await query.edit_message_text(
        f"👥 Твоя ссылка:\n{link}",
        reply_markup=menu()
    )

async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    users = cur.execute("SELECT user_id, coins FROM users ORDER BY coins DESC LIMIT 10").fetchall()
    text = "🏆 ТОП\n\n"
    i = 1
    for u in users:
        text += f"{i}. {u[0]} — {u[1]} 💰\n"
        i += 1
    await query.edit_message_text(text, reply_markup=menu())
async def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(click,"click"))
    app.add_handler(CallbackQueryHandler(profile, pattern="profile"))
    app.add_handler(CallbackQueryHandler(ref, pattern="ref"))
    app.add_handler(CallbackQueryHandler(top, pattern="top"))
    print("Bot started")
    app.run_polling()
    
    if __name__ == "main":
        main()