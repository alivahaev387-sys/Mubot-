import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
import json, random, time, sqlite3

# ===== ТОКЕН И НАСТРОЙКИ =====
TOKEN = "vk1.a.Fgowv-iH2wbOXG7ra56zmUWabQJy2OBRma9n4V3ufueJ_FJrbt5K_t9dOu_OtC-xF1iTWBi8yX5bGOmQ1kbQExof1U4IZKgoO6NVGNg9aaR17ECXar65GK6s-LdkflKto0qhZddvXHeDhxkFeya3z5XN80QnNGB7F676pFOs4xScHkUyvyvodMk5QsFpDHSrJ45m23CVzidcr1reHfrqW5ci9FxMDEhiF3JGG1021qQ"
GROUP_ID = 243089386
ADMIN_ID = 200005093141 

vk_session = vk_api.VkApi(token=TOKEN)
longpoll = VkBotLongPoll(vk_session, GROUP_ID)
vk = vk_session.get_api()

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect('casino.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS players 
                 (user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 1000)''')
    c.execute('''CREATE TABLE IF NOT EXISTS promos 
                 (code TEXT PRIMARY KEY, amount INTEGER)''')
    conn.commit()
    conn.close()

def get_balance(user_id):
    conn = sqlite3.connect('casino.db')
    c = conn.cursor()
    c.execute("SELECT balance FROM players WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    if not row:
        c.execute("INSERT INTO players (user_id, balance) VALUES (?, 1000)", (user_id,))
        conn.commit()
        row = (1000,)
    conn.close()
    return row[0]

def set_balance(user_id, amount):
    conn = sqlite3.connect('casino.db')
    c = conn.cursor()
    c.execute("UPDATE players SET balance = ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

def add_promo(name, amount):
    conn = sqlite3.connect('casino.db')
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO promos (code, amount) VALUES (?, ?)", (name.upper(), amount))
    conn.commit()
    conn.close()

def use_promo(name):
    conn = sqlite3.connect('casino.db')
    c = conn.cursor()
    c.execute("SELECT amount FROM promos WHERE code = ?", (name.upper(),))
    row = c.fetchone()
    if row:
        c.execute("DELETE FROM promos WHERE code = ?", (name.upper(),))
        conn.commit()
        conn.close()
        return row[0]
    conn.close()
    return None

init_db()

# --- ОТПРАВКА СООБЩЕНИЙ ---
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

def get_activate_kb():
    return json.dumps({
        "inline": True,
        "buttons": [
            [{"action": {"type": "callback", "label": "🎮 Активировать", "payload": json.dumps({"cmd": "activate"})}, "color": "positive"}]
        ]
    }, ensure_ascii=False)

print("БОТ ЗАПУЩЕН С БАЗОЙ ДАННЫХ!")

while True:
    try:
        for event in longpoll.listen():
            
            # 1. Добавление в беседу
            if event.type == VkBotEventType.MESSAGE_NEW and event.object.message.get('action'):
                action = event.object.message['action']
                if action.get('type') == 'chat_invite_user' and action.get('member_id') == -GROUP_ID:
                    peer_id = event.object.message['peer_id']
                    cm_id = event.object.message.get('conversation_message_id')
                    send_msg(peer_id, "Привет! Я игровой бот.\nНажми на кнопку, чтобы включить игры.", get_activate_kb(), reply_to=cm_id)
                    continue

            # 2. Нажатие кнопки активации
            if event.type == VkBotEventType.MESSAGE_EVENT:
                payload = event.object.payload
                if payload.get("cmd") == "activate":
                    vk.messages.sendMessageEventAnswer(event_id=event.object.event_id, user_id=event.object.user_id, peer_id=event.object.peer_id, event_data=json.dumps({"type": "show_snackbar", "text": "✅ Успешно!"}))
                    send_msg(event.object.peer_id, "✅ Бот активирован в этой беседе!\nПиши /help.")
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

                balance = get_balance(user_id)
                is_ls = (peer_id == user_id)

                # Игры
                if text_lower.startswith("/красное"):
                    if len(parts) == 2 and parts[1].isdigit():
                        bet = int(parts[1])
                        if bet > balance or bet < 10:
                            send_msg(peer_id, f"❌ Ошибка: мин. ставка 10, баланс {balance}.", reply_to=cm_id)
                        else:
                            res = random.randint(0, 36)
                            if res in [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]:
                                set_balance(user_id, balance + bet)
                                send_msg(peer_id, f"🎉 ПОБЕДА! Выпало {res} 🔴. Ты выиграл {bet}!", reply_to=cm_id)
                            else:
                                set_balance(user_id, balance - bet)
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
                            if res != 0 and res not in [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]:
                                set_balance(user_id, balance + bet)
                                send_msg(peer_id, f"🎉 ПОБЕДА! Выпало {res} ⚫. Ты выиграл {bet}!", reply_to=cm_id)
                            else:
                                set_balance(user_id, balance - bet)
                                send_msg(peer_id, f"😔 ПРОИГРЫШ. Выпало {res}. Ты потерял {bet}.", reply_to=cm_id)
                    else:
                        send_msg(peer_id, "❌ Напиши: /черное [сумма].", reply_to=cm_id)

                elif text_lower.startswith("/чет"):
                    if len(parts) == 2 and parts[1].isdigit():
                        bet = int(parts[1])
                        if bet > balance or bet < 10:
                            send_msg(peer_id, f"❌ Ошибка: мин. ставка 10, баланс {balance}.", reply_to=cm_id)
                        else:
                            res = random.randint(0, 36)
                            if res != 0 and res % 2 == 0:
                                set_balance(user_id, balance + bet)
                                send_msg(peer_id, f"🎉 ПОБЕДА! Выпало {res}. Ты выиграл {bet}!", reply_to=cm_id)
                            else:
                                set_balance(user_id, balance - bet)
                                send_msg(peer_id, f"😔 ПРОИГРЫШ. Выпало {res}. Ты потерял {bet}.", reply_to=cm_id)
                    else:
                        send_msg(peer_id, "❌ Напиши: /чет [сумма].", reply_to=cm_id)

                elif text_lower.startswith("/нечет"):
                    if len(parts) == 2 and parts[1].isdigit():
                        bet = int(parts[1])
                        if bet > balance or bet < 10:
                            send_msg(peer_id, f"❌ Ошибка: мин. ставка 10, баланс {balance}.", reply_to=cm_id)
                        else:
                            res = random.randint(0, 36)
                            if res != 0 and res % 2 != 0:
                                set_balance(user_id, balance + bet)
                                send_msg(peer_id, f"🎉 ПОБЕДА! Выпало {res}. Ты выиграл {bet}!", reply_to=cm_id)
                            else:
                                set_balance(user_id, balance - bet)
                                send_msg(peer_id, f"😔 ПРОИГРЫШ. Выпало {res}. Ты потерял {bet}.", reply_to=cm_id)
                    else:
                        send_msg(peer_id, "❌ Напиши: /нечет [сумма].", reply_to=cm_id)

                elif text_lower.startswith("/дрим"):
                    if len(parts) == 3 and parts[1].isdigit() and parts[2].isdigit():
                        num = int(parts[1])
                        bet = int(parts[2])
                        if 1 <= num <= 15 and bet >= 10 and bet <= balance:
                            res = random.randint(1, 15)
                            if res == num:
                                set_balance(user_id, balance + bet * 10)
                                send_msg(peer_id, f"🔥 ДЖЕКПОТ! Выпало {res}. Ты выиграл x10: +{bet * 10}!", reply_to=cm_id)
                            else:
                                set_balance(user_id, balance - bet)
                                send_msg(peer_id, f"😔 ПРОИГРЫШ. Выпало {res}. Ты потерял {bet}.", reply_to=cm_id)
                        else:
                            send_msg(peer_id, "❌ Ошибка: число от 1 до 15, ставка от 10.", reply_to=cm_id)
                    else:
                        send_msg(peer_id, "❌ Напиши: /дрим [1-15] [сумма].", reply_to=cm_id)

                elif text_lower.startswith("/rps"):
                    if len(parts) == 3 and parts[1] in ["камень", "ножницы", "бумага"] and parts[2].isdigit():
                        choice = parts[1]
                        bet = int(parts[2])
                        if bet >= 10 and bet <= balance:
                            bot = random.choice(["камень", "ножницы", "бумага"])
                            if choice == bot:
                                send_msg(peer_id, f"🤝 НИЧЬЯ!\nТы: {choice}\nБот: {bot}", reply_to=cm_id)
                            elif (choice == "камень" and bot == "ножницы") or (choice == "ножницы" and bot == "бумага") or (choice == "бумага" and bot == "камень"):
                                set_balance(user_id, balance + bet)
                                send_msg(peer_id, f"🎉 ПОБЕДА!\nТы: {choice}\nБот: {bot}\nТы выиграл {bet}!", reply_to=cm_id)
                            else:
                                set_balance(user_id, balance - bet)
                                send_msg(peer_id, f"😔 ПРОИГРЫШ.\nТы: {choice}\nБот: {bot}\nТы потерял {bet}.", reply_to=cm_id)
                        else:
                            send_msg(peer_id, "❌ Неверная ставка.", reply_to=cm_id)
                    else:
                        send_msg(peer_id, "❌ Напиши: /rps [камень/ножницы/бумага] [сумма].", reply_to=cm_id)

                # Промокоды
                elif text_lower.startswith("/создать промокод"):
                    if user_id != ADMIN_ID:
                        send_msg(peer_id, "❌ Нет прав.", reply_to=cm_id)
                        continue
                    if len(parts) == 4 and parts[3].isdigit():
                        add_promo(parts[2].upper(), int(parts[3]))
                        send_msg(peer_id, f"✅ Промокод {parts[2].upper()} на {parts[3]} монет создан!", reply_to=cm_id)
                    else:
                        send_msg(peer_id, "❌ Напиши: /создать промокод [название] [сумма]", reply_to=cm_id)

                elif text_lower.startswith("/promo"):
                    if len(parts) == 2:
                        name = parts[1].upper()
                        amount = use_promo(name)
                        if amount:
                            set_balance(user_id, balance + amount)
                            send_msg(peer_id, f"🎁 Промокод {name} активирован! +{amount} монет.", reply_to=cm_id)
                        else:
                            send_msg(peer_id, "❌ Неверное название или промокод уже использован.", reply_to=cm_id)
                    else:
                        send_msg(peer_id, "❌ Напиши: /promo [название]", reply_to=cm_id)

                # Остальное
                elif text_lower == "/help":
                    help_text = ("📖 Команды:\n\n"
                                 "🔴 /красное [сумма]\n"
                                 "⚫ /черное [сумма]\n"
                                 "🟢 /чет [сумма]\n"
                                 "🔴 /нечет [сумма]\n"
                                 "🔢 /дрим [1-15] [сумма]\n"
                                 "✂️ /rps [камень/ножницы/бумага] [сумма]\n"
                                 "🎁 /promo [название]\n\n"
                                 "👤 /профиль\n"
                                 "🏆 /топ")
                    
                    # Если админ, показываем ему секретную команду
                    if user_id == ADMIN_ID:
                        help_text += "\n\n👑 Для админа:\n/создать промокод [название] [сумма]"
                        
                    send_msg(peer_id, help_text, reply_to=cm_id)
                
                elif text_lower in ["начать", "start", "меню"]:
                    if is_ls:
                        send_msg(peer_id, "🎰 Спасибо, что выбрали именно наш бот!\nВведи /help, чтобы увидеть команды.", reply_to=cm_id)
                
                elif "профиль" in text_lower or "/профиль" in text_lower:
                    send_msg(peer_id, f"👤 Профиль:\n💰 Баланс: {balance} монет", reply_to=cm_id)
                
                elif "топ" in text_lower or "/топ" in text_lower:
                    conn = sqlite3.connect('casino.db')
                    c = conn.cursor()
                    c.execute("SELECT user_id, balance FROM players ORDER BY balance DESC LIMIT 5")
                    top = c.fetchall()
                    conn.close()
                    top_text = "🏆 Топ 5 богачей:\n\n"
                    if not top: top_text += "Пока никого нет."
                    else:
                        for i, (u, b) in enumerate(top, 1):
                            top_text += f"{i}. [id{u}|Игрок] — {b} монет\n"
                    send_msg(peer_id, top_text, reply_to=cm_id)
                
                # Если бот не знает команду — просто ИГНОРИРУЕТ

    except Exception as e:
        print(f"⚠️ Ошибка: {e}")
        time.sleep(2)
