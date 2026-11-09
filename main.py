import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
import json, random, time
import sqlite3

# ===== ТОКЕН И НАСТРОЙКИ =====
TOKEN = "vk1.a.Fgowv-iH2wbOXG7ra56zmUWabQJy2OBRma9n4V3ufueJ_FJrbt5K_t9dOu_OtC-xF1iTWBi8yX5bGOmQ1kbQExof1U4IZKgoO6NVGNg9aaR17ECXar65GK6s-LdkflKto0qhZddvXHeDhxkFeya3z5XN80QnNGB7F676pFOs4xScHkUyvyvodMk5QsFpDHSrJ45m23CVzidcr1reHfrqW5ci9FxMDEhiF3JGG1021qQ"
GROUP_ID = 243089386
ADMIN_ID = 200005093141 

vk_session = vk_api.VkApi(token=TOKEN)
longpoll = VkBotLongPoll(vk_session, GROUP_ID)
vk = vk_session.get_api()

# Хранилище для активации бесед и ожидания ставок
active_chats = set()
waiting_for_bet = {}

# ===== БАЗА ДАННЫХ (SQLite) =====
def init_db():
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 1000)''')
    c.execute('''CREATE TABLE IF NOT EXISTS promos
                 (code TEXT PRIMARY KEY, reward INTEGER)''')
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

def set_balance(user_id, amount):
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO users (user_id, balance) VALUES (?, ?)", (user_id, amount))
    conn.commit()
    conn.close()

def update_balance(user_id, amount):
    balance = get_balance(user_id)
    set_balance(user_id, balance + amount)

# ===== ФУНКЦИИ ОТПРАВКИ =====
def send_msg(peer_id, message, keyboard=None, reply_to=None):
    try:
        params = {
            'peer_id': peer_id,
            'message': message,
            'random_id': random.randint(1, 2**31 - 1)
        }
        if keyboard: params['keyboard'] = keyboard
        if reply_to: params['reply_to'] = reply_to
        return vk.messages.send(**params)
    except Exception as e:
        print(f"Ошибка отправки: {e}")

def edit_msg(peer_id, cm_id, message):
    try:
        vk.messages.edit(peer_id=peer_id, message=message, conversation_message_id=cm_id)
    except Exception as e:
        print(f"Ошибка редактирования: {e}")

# ===== КЛАВИАТУРЫ =====
def get_main_kb():
    return json.dumps({
        "one_time": False, 
        "buttons": [
            [{"action": {"type": "text", "label": "🎰 Казино"}, "color": "positive"},
             {"action": {"type": "text", "label": "🎲 Рулетка"}, "color": "primary"}],
            [{"action": {"type": "text", "label": "🚕 Такси"}, "color": "secondary"},
             {"action": {"type": "text", "label": "🎣 Рыбалка"}, "color": "secondary"},
             {"action": {"type": "text", "label": "🏹 Охота"}, "color": "secondary"}],
            [{"action": {"type": "text", "label": "👤 Профиль"}, "color": "secondary"},
             {"action": {"type": "text", "label": "📖 Помощь"}, "color": "negative"}]
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
print("БОТ ЗАПУЩЕН!")

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

            # 2. Нажатие кнопки активации
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
                            edit_msg(peer_id, cm_id, "Отлично! У бота теперь есть администратор. Чтобы пользоваться, напишите /help")
                        else:
                            vk.messages.sendMessageEventAnswer(event_id=event_id, user_id=user_id, peer_id=peer_id, event_data=json.dumps({"type": "show_snackbar", "text": "❌ Вы не администратор беседы!"}))
                    except Exception as e:
                        print(f"Ошибка проверки: {e}")
                continue

            # 3. Текстовые сообщения
            if event.type == VkBotEventType.MESSAGE_NEW and event.object.message.get('text'):
                msg = event.object.message
                peer_id = msg['peer_id']
                user_id = msg['from_id'] 
                cm_id = msg.get('conversation_message_id')
                
                text = msg.get('text', '').strip()
                text_lower = text.lower()
                parts = text_lower.split()
                is_ls = (peer_id == user_id)

                # Игнорируем беседы, где не активирован
                if not is_ls and peer_id not in active_chats:
                    continue

                balance = get_balance(user_id)

                # --- ЛОГИКА ДЛЯ БЕСЕД (СТРОГО КОМАНДЫ) ---
                if not is_ls:
                    if text_lower == "/help":
                        help_text = ("📖 Команды:\n\n"
                                     "🔴 /красное [сумма]\n"
                                     "⚫ /черное [сумма]\n"
                                     "✂️ /rps [камень/ножницы/бумага] [сумма]\n"
                                     "🚕 /такси\n"
                                     "🎣 /рыбалка\n"
                                     "🏹 /охота\n"
                                     "👤 /профиль\n"
                                     "🏆 /топ")
                        send_msg(peer_id, help_text, reply_to=cm_id)
                    
                    elif text_lower.startswith("/красное"):
                        if len(parts) == 2 and parts[1].isdigit():
                            bet = int(parts[1])
                            if bet > balance or bet < 10:
                                send_msg(peer_id, f"❌ Ошибка: мин. ставка 10, баланс {balance}.", reply_to=cm_id)
                            else:
                                res = random.randint(0, 36)
                                if res in [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]:
                                    update_balance(user_id, bet)
                                    send_msg(peer_id, f"🎉 ПОБЕДА! Выпало {res} 🔴. Ты выиграл {bet}!", reply_to=cm_id)
                                else:
                                    update_balance(user_id, -bet)
                                    send_msg(peer_id, f"😔 ПРОИГРЫШ. Выпало {res}. Ты потерял {bet}.", reply_to=cm_id)
                        else:
                            send_msg(peer_id, "❌ Напиши: /красное [сумма].", reply_to=cm_id)

                    elif text_lower.startswith("/черное"):
                        if len(parts) == 2 and parts[1].isdigit():
                            bet = int(parts[1])
                            if bet > balance or bet < 10:
                                send_msg(peer_id, f"❌ Ошибка: мин. ставка 10, баланс {balance}.", reply_to=cm_id)
                            else:
                                res = random.randint(0, 36)
                                if res in [2,4,6,8,10,11,13,15,17,20,22,24,26,28,29,31,33,35]:
                                    update_balance(user_id, bet)
                                    send_msg(peer_id, f"🎉 ПОБЕДА! Выпало {res} ⚫. Ты выиграл {bet}!", reply_to=cm_id)
                                else:
                                    update_balance(user_id, -bet)
                                    send_msg(peer_id, f"😔 ПРОИГРЫШ. Выпало {res}. Ты потерял {bet}.", reply_to=cm_id)
                        else:
                            send_msg(peer_id, "❌ Напиши: /черное [сумма].", reply_to=cm_id)
                    
                    elif text_lower == "/такси":
                        earned = random.randint(50, 200)
                        update_balance(user_id, earned)
                        send_msg(peer_id, f"🚕 Ты заработал на такси {earned} монет!", reply_to=cm_id)
                    elif text_lower == "/рыбалка":
                        earned = random.randint(20, 300)
                        update_balance(user_id, earned)
                        send_msg(peer_id, f"🎣 Ты поймал рыбу на {earned} монет!", reply_to=cm_id)
                    elif text_lower == "/охота":
                        earned = random.randint(10, 500)
                        update_balance(user_id, earned)
                        send_msg(peer_id, f"🏹 Ты удачно поохотился на {earned} монет!", reply_to=cm_id)
                    elif text_lower == "/профиль":
                        send_msg(peer_id, f"👤 Твой баланс: {balance} монет", reply_to=cm_id)
                    elif text_lower == "/топ":
                        conn = sqlite3.connect('game.db')
                        c = conn.cursor()
                        c.execute("SELECT user_id, balance FROM users ORDER BY balance DESC LIMIT 5")
                        sorted_players = c.fetchall()
                        conn.close()
                        
                        top_text = "🏆 Топ 5 богачей:\n\n"
                        if not sorted_players: top_text += "Пока никого нет."
                        else:
                            for i, (u, b) in enumerate(sorted_players, 1):
                                top_text += f"{i}. [id{u}|Игрок] — {b} монет\n"
                        send_msg(peer_id, top_text, reply_to=cm_id)

                    # СОЗДАНИЕ ПРОМОКОДА (ТОЛЬКО ДЛЯ ВЛАДЕЛЬЦА)
                    elif text_lower.startswith("/промокод ") and user_id == ADMIN_ID:
                        try:
                            _, code, amount = parts
                            amount = int(amount)
                            conn = sqlite3.connect('game.db')
                            c = conn.cursor()
                            c.execute("INSERT INTO promos (code, reward) VALUES (?, ?)", (code, amount))
                            conn.commit()
                            conn.close()
                            send_msg(peer_id, f"✅ Промокод `{code}` на {amount} монет создан!", reply_to=cm_id)
                        except:
                            send_msg(peer_id, "❌ Формат: /промокод название сумма", reply_to=cm_id)

                    # АКТИВАЦИЯ ПРОМОКОДА
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
                                send_msg(peer_id, f"✅ Промокод активирован! Вы получили {reward} монет.", reply_to=cm_id)
                            else:
                                send_msg(peer_id, "❌ Такого промокода нет или он уже активирован.", reply_to=cm_id)
                            conn.close()
                        except:
                            send_msg(peer_id, "❌ Формат: /promo название", reply_to=cm_id)
                    
                    continue

                # --- ЛОГИКА ДЛЯ ЛС (КНОПКИ И КОМАНДЫ) ---
                if text_lower in ["начать", "start", "меню"]:
                    send_msg(peer_id, f"🎰 Твой баланс: {balance} монет.\nВыбирай игру на кнопках ниже 👇", get_main_kb(), reply_to=cm_id)
                
                elif text == "🎰 Казино" or text == "🎲 Рулетка":
                    waiting_for_bet[user_id] = "casino"
                    send_msg(peer_id, "Напиши сумму ставки (например: 500):", get_main_kb(), reply_to=cm_id)
                elif text == "🚕 Такси":
                    earned = random.randint(50, 200)
                    update_balance(user_id, earned)
                    send_msg(peer_id, f"🚕 Ты поработал таксистом и заработал {earned} монет!", get_main_kb(), reply_to=cm_id)
                elif text == "🎣 Рыбалка":
                    earned = random.randint(20, 300)
                    update_balance(user_id, earned)
                    send_msg(peer_id, f"🎣 Ты поймал рыбу и продал за {earned} монет!", get_main_keyboard=None, reply_to=cm_id) # Опечатка исправлена ниже
                    send_msg(peer_id, f"🎣 Ты поймал рыбу и продал за {earned} монет!", get_main_kb(), reply_to=cm_id)
                elif text == "🏹 Охота":
                    earned = random.randint(10, 500)
                    update_balance(user_id, earned)
                    send_msg(peer_id, f"🏹 Ты удачно поохотился и заработал {earned} монет!", get_main_kb(), reply_to=cm_id)
                elif text == "👤 Профиль":
                    send_msg(peer_id, f"👤 Твой баланс: {balance} монет", get_main_kb(), reply_to=cm_id)
                elif text == "📖 Помощь":
                    send_msg(peer_id, "📖 Жми на кнопки, чтобы играть и зарабатывать!", get_main_kb(), reply_to=cm_id)
                
                # Обработка ставки в ЛС
                elif user_id in waiting_for_bet:
                    if text.isdigit():
                        bet = int(text)
                        del waiting_for_bet[user_id]
                        
                        if bet > balance or bet < 10:
                            send_msg(peer_id, f"❌ Ошибка: мин. ставка 10, баланс {balance}.", get_main_kb(), reply_to=cm_id)
                        else:
                            res = random.randint(0, 36)
                            if res % 2 != 0 and res != 0: # Выигрыш на нечет
                                update_balance(user_id, bet)
                                send_msg(peer_id, f"🎉 ПОБЕДА! Выпало {res} 🔴. Ты выиграл {bet}!", get_main_kb(), reply_to=cm_id)
                            else:
                                update_balance(user_id, -bet)
                                send_msg(peer_id, f"😔 ПРОИГРЫШ. Выпало {res}. Ты потерял {bet}.", get_main_kb(), reply_to=cm_id)
                    else:
                        send_msg(peer_id, "❌ Введи число.", get_main_kb(), reply_to=cm_id)

    except Exception as e:
        print(f"⚠️ Ошибка: {e}")
        time.sleep(2)
