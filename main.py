import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
import json, random, time
import sqlite3

# ===== НАСТРОЙКИ =====
TOKEN = "vk1.a.Fgowv-iH2wbOXG7ra56zmUWabQJy2OBRma9n4V3ufueJ_FJrbt5K_t9dOu_OtC-xF1iTWBi8yX5bGOmQ1kbQExof1U4IZKgoO6NVGNg9aaR17ECXar65GK6s-LdkflKto0qhZddvXHeDhxkFeya3z5XN80QnNGB7F676pFOs4xScHkUyvyvodMk5QsFpDHSrJ45m23CVzidcr1reHfrqW5ci9FxMDEhiF3JGG1021qQ"
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

# ===== ЗАПУСК =====
init_db()
print("БОТ УСПЕШНО ЗАПУЩЕН! Ожидаю сообщения...")

while True:
    try:
        for event in longpoll.listen():
            
            # --- ОБРАБОТКА НАЖАТИЯ "НАЧАТЬ" (ПЕРВОЕ СООБЩЕНИЕ) ---
            if event.type == VkBotEventType.MESSAGE_NEW and event.object.message.get('action'):
                action = event.object.message['action']
                if action.get('type') == 'chat_invite_user' and action.get('member_id') == -GROUP_ID:
                    peer_id = event.object.message['peer_id']
                    kb = json.dumps({"inline": True, "buttons": [[{"action": {"type": "callback", "label": "🎮 Активировать", "payload": json.dumps({"cmd": "activate"})}, "color": "positive"}]]}, ensure_ascii=False)
                    send_msg(peer_id, "Привет! Я игровой бот. Выдай мне админку в беседе и нажми кнопку ниже.", kb)
                    continue

            # --- ОБРАБОТКА КНОПОК ---
            if event.type == VkBotEventType.MESSAGE_EVENT:
                payload = event.object.payload
                peer_id = event.object.peer_id
                user_id = event.object.user_id
                event_id = event.object.event_id
                cm_id = event.object.conversation_message_id
                
                if payload.get("cmd") == "activate":
                    try:
                        members = vk.messages.getConversationMembers(peer_id=peer_id)['items']
                        is_admin = any(m['member_id'] == user_id and m.get('is_admin', False) for m in members)
                        if is_admin:
                            active_chats.add(peer_id)
                            vk.messages.sendMessageEventAnswer(event_id=event_id, user_id=user_id, peer_id=peer_id, event_data=json.dumps({"type": "show_snackbar", "text": "✅ Успешно!"}))
                            vk.messages.edit(peer_id=peer_id, message="Отлично! Бот активирован. Напишите /help", conversation_message_id=cm_id)
                        else:
                            vk.messages.sendMessageEventAnswer(event_id=event_id, user_id=user_id, peer_id=peer_id, event_data=json.dumps({"type": "show_snackbar", "text": "❌ Вы не админ!"}))
                    except Exception as e:
                        print(f"Ошибка кнопки: {e}")
                continue

            # --- ОБРАБОТКА ЛЮБЫХ ТЕКСТОВЫХ СООБЩЕНИЙ ---
            if event.type == VkBotEventType.MESSAGE_NEW:
                msg = event.object.message
                
                # Если это ЛС, и текста нет (нажали "Начать" или стикер) — шлем меню
                if msg['peer_id'] == msg['from_id'] and not msg.get('text'):
                    send_msg(msg['peer_id'], f"👋 Привет! Твой баланс: {get_balance(msg['from_id'])}$\nВыбирай действие:", get_main_kb())
                    continue

                if not msg.get('text'):
                    continue # Если в беседе пустое сообщение, игнорируем

                text = msg.get('text', '').strip()
                text_lower = text.lower()
                parts = text_lower.split()
                user_id = msg['from_id']
                peer_id = msg['peer_id']
                cm_id = msg.get('conversation_message_id')
                is_ls = (peer_id == user_id)

                # Если бот в беседе, но его не активировали — молчим
                if not is_ls and peer_id not in active_chats:
                    continue

                balance = get_balance(user_id)

                # --- ЛОГИКА БЕСЕД ---
                if not is_ls:
                    if text_lower in ["/help", "/start"]:
                        send_msg(peer_id, "📖 Команды:\n/работа\n/профиль\n/топ\n/promo код", reply_to=cm_id)
                    elif text_lower == "/работа":
                        earned = random.randint(500, 1500)
                        update_balance(user_id, earned)
                        send_msg(peer_id, f"💼 Ты заработал {earned}$! Баланс: {get_balance(user_id)}$", reply_to=cm_id)
                    elif text_lower == "/профиль":
                        send_msg(peer_id, f"👤 Твой баланс: {balance}$", reply_to=cm_id)
                    elif text_lower.startswith("/promo "):
                        try:
                            code = parts[1]
                            conn = sqlite3.connect('game.db')
                            c = conn.cursor()
                            c.execute("SELECT reward FROM promos WHERE code = ?", (code,))
                            res = c.fetchone()
                            if res:
                                update_balance(user_id, res[0])
                                c.execute("DELETE FROM promos WHERE code = ?", (code,))
                                conn.commit()
                                send_msg(peer_id, f"✅ Промокод активирован! +{res[0]}$", reply_to=cm_id)
                            else:
                                send_msg(peer_id, "❌ Неверный промокод.", reply_to=cm_id)
                            conn.close()
                        except:
                            pass
                    continue

                # --- ЛОГИКА ЛС (МЕНЮ) ---
                # Если написали "начать", "start", "меню" или любую фигню при первом запуске
                if text_lower in ["начать", "start", "begin", "меню", "привет", "hello"]:
                    send_msg(peer_id, f"🎰 Твой баланс: {balance}$\nВыбирай действие на кнопках 👇", get_main_kb(), reply_to=cm_id)
                
                elif text == "💼 Работа":
                    send_msg(peer_id, "Выбери работу:", get_work_kb(), reply_to=cm_id)
                
                elif text == "🔙 Назад":
                    send_msg(peer_id, "Главное меню:", get_main_kb(), reply_to=cm_id)

                elif text in ["🚕 Такси", "🎣 Рыбалка", "🏹 Охота"]:
                    earned = random.randint(200, 800)
                    update_balance(user_id, earned)
                    send_msg(peer_id, f"✅ Ты заработал {earned}$!\n💰 Баланс: {get_balance(user_id)}$", get_work_kb(), reply_to=cm_id)

                elif text == "💣 Сапер":
                    send_msg(peer_id, "💣 В разработке...", get_work_kb(), reply_to=cm_id)
                
                elif text == "🎰 Казино":
                    waiting_for_bet[user_id] = True
                    send_msg(peer_id, f"🎰 Введи сумму ставки (Баланс: {balance}$):", reply_to=cm_id)
                
                elif text == "👤 Профиль":
                    send_msg(peer_id, f"👤 Твой профиль:\n💰 Баланс: {balance}$", get_main_kb(), reply_to=cm_id)
                
                elif text == "📖 Помощь":
                    send_msg(peer_id, "📖 Жми кнопки! Промокод: /promo [код]", get_main_kb(), reply_to=cm_id)
                
                elif user_id in waiting_for_bet:
                    if text.isdigit():
                        bet = int(text)
                        del waiting_for_bet[user_id]
                        if bet > balance or bet < 10:
                            send_msg(peer_id, f"❌ Мин. ставка 10$, у тебя {balance}$", get_main_kb(), reply_to=cm_id)
                        else:
                            res = random.randint(0, 36)
                            if res % 2 != 0 and res != 0:
                                update_balance(user_id, bet)
                                send_msg(peer_id, f"🎉 Победа! Выпало {res} 🔴. +{bet}$", get_main_kb(), reply_to=cm_id)
                            else:
                                update_balance(user_id, -bet)
                                send_msg(peer_id, f"😔 Проигрыш. Выпало {res} ⚫. -{bet}$", get_main_kb(), reply_to=cm_id)
                    else:
                        send_msg(peer_id, "❌ Введи число!", get_main_kb(), reply_to=cm_id)

    except Exception as e:
        print(f"⚠️ Ошибка: {e}")
        time.sleep(1)
