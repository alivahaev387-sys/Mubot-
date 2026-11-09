import random
import asyncio
import aiosqlite
from vkbottle.bot import Bot, Message
from vkbottle import Keyboard, KeyboardButtonColor, Text, GroupEventType

# --- НАСТРОЙКИ ---
TOKEN = "vk1.a.Fgowv-iH2wbOXG7ra56zmUWabQJy2OBRma9n4V3ufueJ_FJrbt5K_t9dOu_OtC-xF1iTWBi8yX5bGOmQ1kbQExof1U4IZKgoO6NVGNg9aaR17ECXar65GK6s-LdkflKto0qhZddvXHeDhxkFeya3z5XN80QnNGB7F676pFOs4xScHkUyvyvodMk5QsFpDHSrJ45m23CVzidcr1reHfrqW5ci9FxMDEhiF3JGG1021qQ"
ADMIN_ID = 200005093141   # Твой ID
GROUP_ID = 243089386      # ID твоего сообщества (без минуса)

bot = Bot(token=TOKEN)
DB_NAME = "game_database.db"

# --- БАЗА ДАННЫХ ---
async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                balance INTEGER DEFAULT 1000,
                job_cooldown INTEGER DEFAULT 0,
                last_saper INTEGER DEFAULT 0
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS promocodes (
                code TEXT PRIMARY KEY,
                reward INTEGER
            )
        """)
        await db.commit()

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
async def get_user(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            user = await cursor.fetchone()
            if not user:
                await db.execute("INSERT INTO users (user_id, balance) VALUES (?, ?)", (user_id, 1000))
                await db.commit()
                return (user_id, 1000, 0, 0)
            return user

async def update_balance(user_id: int, amount: int):
    await get_user(user_id)
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        await db.commit()

async def get_balance(user_id: int):
    user = await get_user(user_id)
    return user[1]

# --- КЛАВИАТУРЫ ---
def get_main_keyboard():
    kb = Keyboard(one_time=False)
    kb.add(Text("💼 Работа"), color=KeyboardButtonColor.POSITIVE)
    kb.add(Text("🎰 Казино"), color=KeyboardButtonColor.PRIMARY)
    kb.row()
    kb.add(Text("👤 Профиль"), color=KeyboardButtonColor.SECONDARY)
    kb.add(Text("🏆 Топ"), color=KeyboardButtonColor.SECONDARY)
    kb.row()
    kb.add(Text("🎁 Промокод"), color=KeyboardButtonColor.SECONDARY)
    return kb

# --- ОБРАБОТЧИКИ ---

# 1. Приветствие в ЛС (игнорируем регистр)
@bot.on.message(text=["Начать", "начать", "start"], ignore_case=True)
async def start_handler(message: Message):
    # Проверяем, что это ЛС (peer_id равен from_id)
    if message.peer_id != message.from_id:
        return
    await get_user(message.from_id)
    await message.answer(
        "👋 Привет! Я игровой бот.\nВыбирай действие на клавиатуре ниже 👇",
        keyboard=get_main_keyboard()
    )

# 2. Работа
@bot.on.message(text=["💼 Работа"])
async def work_handler(message: Message):
    reward = random.randint(500, 1500)
    await update_balance(message.from_id, reward)
    await message.answer(f"💼 Ты поработал и заработал **{reward}$**!\n💰 Твой баланс: {await get_balance(message.from_id)}$")

# 3. Профиль
@bot.on.message(text=["👤 Профиль"])
async def profile_handler(message: Message):
    balance = await get_balance(message.from_id)
    await message.answer(f"👤 Твой профиль:\n💰 Баланс: {balance}$\n🆔 ID: {message.from_id}")

# 4. Топ
@bot.on.message(text=["🏆 Топ"])
async def top_handler(message: Message):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT user_id, balance FROM users ORDER BY balance DESC LIMIT 5") as cursor:
            top_users = await cursor.fetchall()
            
    text = "🏆 **Топ 5 богатейших:**\n\n"
    for i, (uid, bal) in enumerate(top_users, 1):
        text += f"{i}. ID {uid} — {bal}$\n"
    await message.answer(text)

# 5. Команда /help
@bot.on.message(text="/help", ignore_case=True)
async def help_handler(message: Message):
    help_text = (
        "📚 **Доступные команды:**\n"
        "/help — Список команд\n"
        "/balance — Мой баланс\n"
        "/promo [код] — Активировать промокод\n\n"
        "В личных сообщениях бота есть меню с кнопками!"
    )
    await message.answer(help_text, reply_to=message.id)

# 6. Баланс
@bot.on.message(text="/balance", ignore_case=True)
async def balance_handler(message: Message):
    bal = await get_balance(message.from_id)
    await message.answer(f"💰 Ваш баланс: {bal}$", reply_to=message.id)

# 7. Активация промокода
@bot.on.message(text="/promo <code>", ignore_case=True)
async def activate_promo_handler(message: Message, code: str):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT reward FROM promocodes WHERE code = ?", (code,)) as cursor:
            promo = await cursor.fetchone()
            
            if promo:
                reward = promo[0]
                await update_balance(message.from_id, reward)
                await db.execute("DELETE FROM promocodes WHERE code = ?", (code,))
                await db.commit()
                await message.reply(f"✅ Промокод активирован! Вы получили {reward}$")
            else:
                await message.reply("❌ Такого промокода не существует или он уже активирован.")

# 8. Создание промокода (Владелец)
@bot.on.message(text="/промокод <name> <amount:int>", ignore_case=True)
async def create_promo_handler(message: Message, name: str, amount: int):
    if message.from_id != ADMIN_ID:
        return 
        
    async with aiosqlite.connect(DB_NAME) as db:
        try:
            await db.execute("INSERT INTO promocodes (code, reward) VALUES (?, ?)", (name, amount))
            await db.commit()
            await message.reply(f"✅ Промокод `{name}` на сумму {amount}$ успешно создан!")
        except aiosqlite.IntegrityError:
            await message.reply("❌ Такой промокод уже существует.")

# 9. Приветствие при добавлении БОТА в беседу
@bot.on.raw_event(GroupEventType.CHAT_INVITE_USER, dataclass=dict)
async def on_chat_invite(event_data: dict):
    # Проверяем, что добавили именно бота (ID группы со знаком минус)
    if event_data['object']['member_id'] == -GROUP_ID:
        kb = Keyboard(inline=True)
        # Важно: payload должен быть строкой JSON или словарем
        kb.add(Text("Активировать", payload={"cmd": "activate_chat"}), color=KeyboardButtonColor.POSITIVE)
        
        await bot.api.messages.send(
            peer_id=event_data['object']['peer_id'],
            message="👋 Привет! Я игровой бот. Нажмите кнопку ниже, чтобы активировать меня в этом чате.\n(Активация доступна только владельцу бота).",
            keyboard=kb.get_json(),
            random_id=0
        )

# 10. Обработка нажатия кнопки "Активировать"
@bot.on.message(payload={"cmd": "activate_chat"})
async def activate_chat_handler(message: Message):
    if message.from_id != ADMIN_ID:
        await message.answer("❌ Ошибка! Только владелец бота может активировать его здесь.")
        return
    
    # Убираем кнопку, редактируя сообщение
    await bot.api.messages.edit(
        peer_id=message.peer_id,
        message="Отлично! У бота теперь есть администратор. Напиши /help, чтобы узнать все команды. ❤️",
        conversation_message_id=message.conversation_message_id
    )

# Запуск
async def main():
    await init_db()
    print("Бот успешно запущен и готов к работе!")
    await bot.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
