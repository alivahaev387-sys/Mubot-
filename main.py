import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
import json, random, time, os

# ===== НАСТРОЙКИ =====
TOKEN = "vk1.a.n-y1VnQMFI87cAGH7zXHwYy6LncLM_UuAaCihe6dlWxUBLGwS8no-KjRmFrA9zmwy-STfP7f2VZOHArq1-WVKYVRUA3H1F3-pO5gtXRxEziw3u3st-dTYHNiK_an2ZcbUIpXYNy98HHTGQv12wFtMLsSASQ0kO0ke0B0DRsXc7hn-LQrYcpbu54a_kQmP7dxBO5a8gTmuS9Dn9LH7oMLfE6G6_GPJZxJAgkwzptCnWw"
GROUP_ID = 243089386
ADMIN_ID = 200005093141 

vk_session = vk_api.VkApi(token=TOKEN)
longpoll = VkBotLongPoll(vk_session, GROUP_ID)
vk = vk_session.get_api()

# ===== БАЗА ДАННЫХ (JSON) =====
DB_FILE = "database.json"

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"users": {}, "promos": {}, "active_chats": []}

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

db = load_db()
waiting_for_bet = {}

def get_balance(user_id):
    uid = str(user_id)
    if uid not in db["users"]:
        db["users"][uid] = 1000
        save_db(db)
    return db["users"][uid]

def update_balance(user_id, amount):
    uid = str(user_id)
    db["users"][uid] = get_balance(user_id) + amount
    save_db(db)

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
            [{"action": {"type": "text", "label": "🏹 Охота"}, "color": "primary"}, {"action": {"type": "text", "label": "🔙 Назад"}, "color": "secondary"}]
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
print("ИГРОВОЙ БОТ УСПЕШНО ЗАПУЩЕН!")

while True:
    try:
        for event in longpoll.listen():
            
            # 1. Приглашение в беседу
            if event.type == VkBotEventType.MESSAGE_NEW and event.object.message.get('action'):
                action = event.object.message['action']
                if action.get('type') == 'chat_invite_user' and action.get('member_id') == -GROUP_ID:
                    peer_id = event.object.message['peer_id']
                    cm_id = event.object.message.get('conversation_message_id')
                    send_msg(peer_id, "Привет! Я игровой бот.\nВыдай мне админку и нажми кнопку ниже.", get_activate_kb(), reply_to=cm_id)
                    continue

            # 2. Кнопки в беседе
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
                            if peer_id not in db["active_chats"]:
                                db["active_chats"].append(peer_id)
                                save_db(db)
                            vk.messages.sendMessageEventAnswer(event_id=event_id, user_id=user_id, peer_id=peer_id, event_data=json.dumps({"type": "show_snackbar", "text": "✅ Успешно!"}))
                            vk.messages.edit(peer_id=peer_id, message="Отлично! Бот активирован. Напишите /help", conversation_message_id=cm_id)
                        else:
                            vk.messages.sendMessageEventAnswer(event_id=event_id, user_id=user_id, peer_id=peer_id, event_data=json.dumps({"type": "show_snackbar", "text": "❌ Вы не админ!"}))
                    except:
                        pass
                continue

            # 3. Текстовые сообщения
            if event.type == VkBotEventType.MESSAGE_NEW:
                msg = event.object.message
                
                # Кнопка "Начать"
                if msg['peer_id'] == msg['from_id'] and not msg.get('text'):
                    send_msg(msg['peer_id'], f"👋 Привет! Твой баланс: {get_balance(msg['from_id'])}$\nВыбирай действие 👇", get_main_kb())
                    continue

                if not msg.get('text'): continue

                text = msg.get('text', '').strip()
                text_lower = text.lower()
                parts = text_lower.split()
                user_id = msg['from_id']
                peer_id = msg['peer_id']
                cm_id = msg.get('conversation_message_id')
                is_ls = (peer_id == user_id)

                # Игнорируем неактивированные беседы
                if not is_ls and peer_id not in db["active_chats"]:
                    continue

                balance = get_balance(user_id)

                # --- БЕСЕДЫ ---
                if not is_ls:
                    if text_lower in ["/help", "/start"]:
                        send_msg(peer_id, "📖 Команды:\n/работа\n/казино [сумма]\n/профиль\n/топ\n/promo [код]", reply_to=cm_id)
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
                        send_msg(peer_id, f"👤 Твой профиль:\n💰 Баланс: {balance}$", reply_to=cm_id)
                    elif text_lower == "/топ":
                        top = sorted(db["users"].items(), key=lambda x: x[1], reverse=True)[:5]
                        top_text = "🏆 Топ 5:\n" + "\n".join([f"{i}. ID {u} — {b}$" for i, (u, b) in enumerate(top, 1)])
                        send_msg(peer_id, top_text, reply_to=cm_id)
                    elif text_lower.startswith("/промокод ") and user_id == ADMIN_ID:
                        try:
                            _, code, amount = parts
                            db["promos"][code] = int(amount)
                            save_db(db)
                            send_msg(peer_id, f"✅ Промокод {code} на {amount}$ создан!", reply_to=cm_id)
                        except:
                            send_msg(peer_id, "❌ Формат: /промокод название сумма", reply_to=cm_id)
                    elif text_lower.startswith("/promo "):
                        try:
                            code = parts[1]
                            if code in db["promos"]:
                                reward = db["promos"][code]
                                del db["promos"][code]
                                save_db(db)
                                update_balance(user_id, reward)
                                send_msg(peer_id, f"✅ Промокод активирован! +{reward}$", reply_to=cm_id)
                            else:
                                send_msg(peer_id, "❌ Неверный промокод.", reply_to=cm_id)
                        except:
                            send_msg(peer_id, "❌ Формат: /promo код", reply_to=cm_id)
                    continue

                # --- ЛС ---
                if text_lower in ["начать", "start", "begin", "меню"]:
                    send_msg(peer_id, f"🎰 Твой баланс: {balance}$.\nВыбирай действие 👇", get_main_kb(), reply_to=cm_id)
                
                elif text == "💼 Работа":
                    send_msg(peer_id, "Выбери, где хочешь поработать:", get_work_kb(), reply_to=cm_id)
                
                elif text == "🔙 Назад":
                    send_msg(peer_id, "Главное меню:", get_main_kb(), reply_to=cm_id)

                elif text in ["🚕 Такси", "🎣 Рыбалка", "🏹 Охота"]:
                    earned = random.randint(200, 800)
                    update_balance(user_id, earned)
                    send_msg(peer_id, f"✅ Ты заработал {earned}$!\n💰 Баланс: {get_balance(user_id)}$", get_work_kb(), reply_to=cm_id)

                elif text == "🎰 Казино":
                    waiting_for_bet[user_id] = True
                    send_msg(peer_id, f"🎰 Введи сумму ставки (у тебя {balance}$):", get_main_kb(), reply_to=cm_id)
                
                elif text == "👤 Профиль":
                    send_msg(peer_id, f"👤 Твой профиль:\n💰 Баланс: {balance}$", get_main_kb(), reply_to=cm_id)
                
                elif text == "🏆 Топ":
                    top = sorted(db["users"].items(), key=lambda x: x[1], reverse=True)[:5]
                    top_text = "🏆 Топ 5:\n" + "\n".join([f"{i}. ID {u} — {b}$" for i, (u, b) in enumerate(top, 1)])
                    send_msg(peer_id, top_text, get_main_kb(), reply_to=cm_id)
                
                elif text == "📖 Помощь":
                    send_msg(peer_id, "📖 Жми кнопки!\n🎁 Промокод: /promo [код]", get_main_kb(), reply_to=cm_id)
                
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
