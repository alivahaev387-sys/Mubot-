import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
import json, random, time
import sqlite3

# ===== ТОКЕН И НАСТРОЙКИ =====
TOKEN = "vk1.a.n-y1VnQMFI87cAGH7zXHwYy6LncLM_UuAaCihe6dlWxUBLGwS8no-KjRmFrA9zmwy-STfP7f2VZOHArq1-WVKYVRUA3H1F3-pO5gtXRxEziw3u3st-dTYHNiK_an2ZcbUIpXYNy98HHTGQv12wFtMLsSASQ0kO0ke0B0DRsXc7hn-LQrYcpbu54a_kQmP7dxBO5a8gTmuS9Dn9LH7oMLfE6G6_GPJZxJAgkwzptCnWw"
GROUP_ID = 243089386
ADMIN_ID = 200005093141 

vk_session = vk_api.VkApi(token=TOKEN)
longpoll = VkBotLongPoll(vk_session, GROUP_ID)
vk = vk_session.get_api()

active_chats = set()
waiting_for_bet = {}

# ===== БАЗА ДАННЫХ =====
def init_db():
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 1000)''')
    c.execute('''CREATE TABLE IF NOT EXISTS promos (code TEXT PRIMARY KEY, reward INTEGER)''')
    conn.commit()
    conn.close()

def get_balance(user_id):
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    res = c.fetchone()
    if not res:
        c.execute("INSERT INTO users (user_id, balance) VALUES (?, 1000)", (user_id,))
        conn.commit()
        balance = 1000
    else:
        balance = res[0]
    conn.close()
    return balance

def update_balance(user_id, amount):
    balance = get_balance(user_id)
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO users (user_id, balance) VALUES (?, ?)", (user_id, balance + amount))
    conn.commit()
    conn.close()

def send_msg(peer_id, message, keyboard=None, reply_to=None):
    try:
        params = {'peer_id': peer_id, 'message': message, 'random_id': random.randint(1, 2**31 - 1)}
        if keyboard: params['keyboard'] = keyboard
        if reply_to: params['reply_to'] = reply_to
        vk.messages.send(**params)
    except Exception as e:
        print(f"Ошибка отправки: {e}")

# ===== КЛАВИАТУРЫ =====
def get_main_kb():
    return json.dumps({
        "one_time": False, 
        "buttons": [
            [{"action": {"type": "text", "label": "💼 Работа"}, "color": "positive"}, {"action": {"type": "text", "label": "🎰 Казино"}, "color": "primary"}],
            [{"action": {"type": "text", "label": "👤 Профиль"}, "color": "secondary"}, {"action": {"type": "text", "label": "🏆 Топ"}, "color": "secondary"}],
            [{"action": {"type": "text", "label": "📖 Помощь"}, "color": "negative"}]
        ]
    }, ensure_ascii=False)

def get_work_kb():
    return json.dumps({
        "one_time": False, 
        "buttons": [
            [{"action": {"type": "text", "label": "🚕 Такси"}, "color": "primary"}, {"action": {"type": "text", "label": "🎣 Рыбалка"}, "color": "primary"}],
            [{"action": {"type": "text", "label": "🏹 Охота"}, "color": "primary"}, {"action": {"type": "text", "label": "💣 Сапер"}, "color": "negative"}],
            [{"action": {"type": "text", "label": "🔙 Назад"}, "color": "secondary"}]
        ]
    }, ensure_ascii=False)

def get_activate_kb():
    return json.dumps({
        "inline": True,
        "buttons": [
            [{"action": {"type": "callback", "label": "🎮 Активировать", "payload": json.dumps({"cmd": "activate"})}, "color": "positive"}]
        ]
    }, ensure_ascii=False)

# ===== ЗАПУСК =====
init_db()
print("БОТ УСПЕШНО ЗАПУЩЕН! Ожидаю сообщения...")

while True:
    try:
        for event in longpoll.listen():
            
            # 1. Приглашение в беседу
            if event.type == VkBotEventType.MESSAGE_NEW and event.object.message.get('action'):
                action = event.object.message['action']
                if action.get('type') == 'chat_invite_user' and action.get('member_id') == -GROUP_ID:
                    peer_id = event.object.message['peer_id']
                    cm_id = event.object.message.get('conversation_message_id')
                    send_msg(peer_id, "Привет! Я игровой бот.\nЧтобы включить игры, выдай мне админку и нажми кнопку ниже.", get_activate_kb(), reply_to=cm_id)
                    continue

            # 2. Нажатие кнопки активации в беседе
            if event.type == VkBotEventType.MESSAGE_EVENT:
                payload = event.object.payload
                peer_id = event.object.peer_id
                user_id = event.object.user_id
                event_id = event.object.event_id
                cm_id = event.object.conversation_message_id
                
                if payload.get("cmd") == "activate":
                    try:
                        members = vk.messages.getConversationMembers(peer_id=peer_id)['items']
                        is_admin = False
                        for m in members:
                            if m['member_id'] == user_id and m.get('is_admin', False):
                                is_admin = True
                                break
                        
                        if is_admin:
                            active_chats.add(peer_id)
                            vk.messages.sendMessageEventAnswer(event_id=event_id, user_id=user_id, peer_id=peer_id, event_data=json.dumps({"type": "show_snackbar", "text": "✅ Успешно!"}))
                            edit_msg(peer_id, cm_id, "Отлично! Бот активирован. Напишите /help")
                        else:
                            vk.messages.sendMessageEventAnswer(event_id=event_id, user_id=user_id, peer_id=peer_id, event_data=json.dumps({"type": "show_snackbar", "text": "❌ Вы не администратор беседы!"}))
                    except Exception as e:
                        print(f"Ошибка проверки админа: {e}")
                continue

            # 3. Текстовые сообщения
            if event.type == VkBotEventType.MESSAGE_NEW:
                msg = event.object.message
                
                # Обработка кнопки "Начать" (пустое сообщение) в ЛС
                if msg['peer_id'] == msg['from_id'] and not msg.get('text'):
                    send_msg(msg['peer_id'], f"👋 Привет! Твой баланс: {get_balance(msg['from_id'])}$\nВыбирай действие на кнопках 👇", get_main_kb())
                    continue

                if not msg.get('text'):
                    continue

                text = msg.get('text', '').strip()
                text_lower = text.lower()
                parts = text_lower.split()
                user_id = msg['from_id']
                peer_id = msg['peer_id']
                cm_id = msg.get('conversation_message_id')
                is_ls = (peer_id == user_id)

                if not is_ls and peer_id not in active_chats:
                    continue

                balance = get_balance(user_id)

                # --- ЛОГИКА ДЛЯ БЕСЕД ---
                if not is_ls:
                    if text_lower in ["/help", "/start"]:
                        send_msg(peer_id, "📖 Команды:\n\n💼 /работа - Заработать\n🎰 /казино [сумма] - Рулетка\n👤 /профиль - Баланс\n🏆 /топ - Богачи\n🎁 /promo [код] - Промокод", reply_to=cm_id)
                    elif text_lower == "/работа":
                        earned = random.randint(500, 1500)
                        update_balance(user_id, earned)
                        send_msg(peer_id, f"💼 Ты заработал {earned}$! Баланс: {get_balance(user_id)}$", reply_to=cm_id)
                    elif text_lower.startswith("/казино"):
                        if len(parts) == 2 and parts[1].isdigit():
                            bet = int(parts[1])
                            if bet > balance or bet < 10:
                                send_msg(peer_id, f"❌ Мин. ставка 10, твой баланс: {balance}$", reply_to=cm_id)
                            else:
                                res = random.randint(0, 36)
                                if res % 2 != 0 and res != 0:
                                    update_balance(user_id, bet)
                                    send_msg(peer_id, f"🎉 ПОБЕДА! Выпало {res} 🔴. Выиграл {bet}$!", reply_to=cm_id)
                                else:
                                    update_balance(user_id, -bet)
                                    send_msg(peer_id, f"😔 ПРОИГРЫШ. Выпало {res} ⚫. Потерял {bet}$.", reply_to=cm_id)
                        else:
                            send_msg(peer_id, "❌ Напиши: /казино [сумма].", reply_to=cm_id)
                    elif text_lower == "/профиль":
                        send_msg(peer_id, f"👤 Твой профиль:\n💰 Баланс: {balance}$\n🆔 ID: {user_id}", reply_to=cm_id)
                    elif text_lower == "/топ":
                        conn = sqlite3.connect('game.db')
                        c = conn.cursor()
                        c.execute("SELECT user_id, balance FROM users ORDER BY balance DESC LIMIT 5")
                        sorted_players = c.fetchall()
                        conn.close()
                        top_text = "🏆 Топ 5 богачей:\n\n"
                        for i, (u, b) in enumerate(sorted_players, 1):
                            top_text += f"{i}. [id{u}|Игрок] — {b}$\n"
                        send_msg(peer_id, top_text, reply_to=cm_id)
                    elif text_lower.startswith("/промокод ") and user_id == ADMIN_ID:
                        try:
                            _, code, amount = parts
                            amount = int(amount)
                            conn = sqlite3.connect('game.db')
                            c = conn.cursor()
                            c.execute("INSERT INTO promos (code, reward) VALUES (?, ?)", (code, amount))
                            conn.commit()
                            conn.close()
                            send_msg(peer_id, f"✅ Промокод `{code}` на {amount}$ создан!", reply_to=cm_id)
                        except:
                            send_msg(peer_id, "❌ Формат: /промокод название сумма", reply_to=cm_id)
                    elif text_lower.startswith("/promo "):
                        try:
                            code = parts[1]
                            conn = sqlite3.connect('game.db')
                            c = conn.cursor()
                            c.execute("SELECT reward FROM promos WHERE code = ?", (code,))
                            res = c.fetchone()
                            if res:
                                reward = res[0]
                                c.execute("DELETE FROM promos WHERE code = ?", (code,))
                                conn.commit()
                                update_balance(user_id, reward)
                                send_msg(peer_id, f"✅ Промокод активирован! Вы получили {reward}$", reply_to=cm_id)
                            else:
                                send_msg(peer_id, "❌ Такого промокода нет или он уже активирован.", reply_to=cm_id)
                            conn.close()
                        except:
                            send_msg(peer_id, "❌ Формат: /promo название", reply_to=cm_id)
                    continue

                # --- ЛОГИКА ДЛЯ ЛС ---
                if text_lower in ["начать", "start", "begin", "меню"]:
                    send_msg(peer_id, f"🎰 Твой баланс: {balance}$.\nВыбирай действие на кнопках ниже 👇", get_main_kb(), reply_to=cm_id)
                
                elif text == "💼 Работа":
                    send_msg(peer_id, "Выбери, где хочешь поработать:", get_work_kb(), reply_to=cm_id)
                
                elif text == "🔙 Назад":
                    send_msg(peer_id, "Главное меню:", get_main_kb(), reply_to=cm_id)

                elif text in ["🚕 Такси", "🎣 Рыбалка", "🏹 Охота"]:
                    earned = random.randint(200, 800)
                    update_balance(user_id, earned)
                    send_msg(peer_id, f"✅ Ты заработал {earned}$!\n💰 Баланс: {get_balance(user_id)}$", get_work_kb(), reply_to=cm_id)

                elif text == "💣 Сапер":
                    send_msg(peer_id, "💣 В разработке... Скоро будет доступно!", get_work_kb(), reply_to=cm_id)

                elif text == "🎰 Казино":
                    waiting_for_bet[user_id] = True
                    send_msg(peer_id, f"🎰 Введи сумму ставки (у тебя {balance}$):", get_main_kb(), reply_to=cm_id)
                
                elif text == "👤 Профиль":
                    send_msg(peer_id, f"👤 Твой профиль:\n💰 Баланс: {balance}$\n🆔 ID: {user_id}", get_main_kb(), reply_to=cm_id)
                
                elif text == "🏆 Топ":
                    conn = sqlite3.connect('game.db')
                    c = conn.cursor()
                    c.execute("SELECT user_id, balance FROM users ORDER BY balance DESC LIMIT 5")
                    sorted_players = c.fetchall()
                    conn.close()
                    top_text = "🏆 Топ 5 богачей:\n\n"
                    for i, (u, b) in enumerate(sorted_players, 1):
                        top_text += f"{i}. ID {u} — {b}$\n"
                    send_msg(peer_id, top_text, get_main_kb(), reply_to=cm_id)
                
                elif text == "📖 Помощь":
                    send_msg(peer_id, "📖 Жми на кнопки, чтобы играть!\n🎁 Промокод активируется командой /promo [код]", get_main_kb(), reply_to=cm_id)
                
                # Обработка ставки в ЛС (Казино)
                elif user_id in waiting_for_bet:
                    if text.isdigit():
                        bet = int(text)
                        del waiting_for_bet[user_id]
                        
                        if bet > balance or bet < 10:
                            send_msg(peer_id, f"❌ Ошибка: мин. ставка 10, твой баланс: {balance}$", get_main_kb(), reply_to=cm_id)
                        else:
                            res = random.randint(0, 36)
                            if res % 2 != 0 and res != 0:
                                update_balance(user_id, bet)
                                send_msg(peer_id, f"🎉 ПОБЕДА! Выпало {res} 🔴. Ты выиграл {bet}$!", get_main_kb(), reply_to=cm_id)
                            else:
                                update_balance(user_id, -bet)
                                send_msg(peer_id, f"😔 ПРОИГРЫШ. Выпало {res} ⚫. Ты потерял {bet}$.", get_main_kb(), reply_to=cm_id)
                    else:
                        send_msg(peer_id, "❌ Введи число.", get_main_kb(), reply_to=cm_id)

    except Exception as e:
        print(f"⚠️ Ошибка: {e}")
        time.sleep(2)
