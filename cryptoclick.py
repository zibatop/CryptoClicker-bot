import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
import sqlite3
import os
import time
import random
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("VK_TOKEN")

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
    user = cur.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
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
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button("⛏ Майнить", VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button("🎁 Бонус", VkKeyboardColor.SECONDARY)
    keyboard.add_button("👤 Профиль", VkKeyboardColor.SECONDARY)
    keyboard.add_line()
    keyboard.add_button("👥 Рефералы", VkKeyboardColor.SECONDARY)
    keyboard.add_button("🏆 ТОП", VkKeyboardColor.SECONDARY)
    return keyboard.get_keyboard()

vk_session = vk_api.VkApi(token=TOKEN)
vk = vk_session.get_api()
longpoll = VkLongPoll(vk_session)

def send(user_id, text):
    vk.messages.send(
        user_id=user_id,
        message=text,
        random_id=random.randint(1, 999999),
        keyboard=menu()
    )

print("TOKEN")

for event in longpoll.listen():
    if event.type == VkEventType.MESSAGE_NEW and event.to_me:
        user_id = event.user_id
        text = event.text.lower()

        user = get_user(user_id)

        if text == "старт":
            send(user_id, "🎮 Добро пожаловать!")

        elif text == "⛏ майнить":
            power = user[2]
            if is_premium(user):
                power *= 2

            coins = user[1] + power

            cur.execute(
                "UPDATE users SET coins=? WHERE user_id=?",
                (coins, user_id)
            )
            conn.commit()

            msg = f"⛏ +{power} монет\n💰 Баланс: {coins}"
            if is_premium(user):
                msg += "\n⭐ ПРЕМИУМ x2"

            send(user_id, msg)

        elif text == "👤 профиль":
            msg = (
                f"👤 Профиль\n\n"
                f"💰 Монеты: {user[1]}\n"
                f"⚡ Клик: {user[2]}\n"
                f"🤖 Роботы: {user[3]}\n"
            )

            if is_premium(user):
                days = (user[6] - int(time.time())) // 86400
                msg += f"⭐ Премиум: {days} дн."

            send(user_id, msg)

        elif text == "🏆 топ":
            users = cur.execute(
                "SELECT user_id, coins FROM users ORDER BY coins DESC LIMIT 10"
            ).fetchall()

            msg = "🏆 ТОП\n\n"
            i = 1
            for u in users:
                msg += f"{i}. id{u[0]} — {u[1]} 💰\n"
                i += 1

            send(user_id, msg)

        elif text == "👥 рефералы":
            link = f"https://vk.me/YOUR_BOT_ID?ref={user_id}"
            send(user_id, f"👥 Твоя ссылка:\n{link}")