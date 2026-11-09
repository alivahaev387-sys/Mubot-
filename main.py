import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
import json, random, time, os

# ===== ТОКЕН И НАСТРОЙКИ =====
TOKEN = "vk1.a.Fgowv-iH2wbOXG7ra56zmUWabQJy2OBRma9n4V3ufueJ_FJrbt5K_t9dOu_OtC-xF1iTWBi8yX5bGOmQ1kbQExof1U4IZKgoO6NVGNg9aaR17ECXar65GK6s-LdkflKto0qhZddvXHeDhxkFeya3z5XN80QnNGB7F676pFOs4xScHkUyvyvodMk5QsFpDHSrJ45m23CVzidcr1reHfrqW5ci9FxMDEhiF3JGG1021qQ"
GROUP_ID = 243089386
ADMIN_ID = 200005093141 

vk_session = vk_api.VkApi(token=TOKEN)
longpoll = VkBotLongPoll(vk_session, GROUP_ID)
vk = vk_session.get_api()

# --- БАЗА ДАННЫХ (JSON файл, чтобы не падало и не сбрасывалось) ---
DB_FILE = "game_db.json"

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"balances": {}, "promos": {}, "active_chats": []}

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

db = load_db()

def get_balance(user_id):
    return db["balances"].get(str(user_id), 1000)

def set_balance(user_id, amount):
    db["balances"][str(user_id)] = amount
    save_db(db)

# --- ФУНКЦИИ ОТПРАВКИ И РЕДАКТИРОВАНИЯ ---
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

def edit_msg(peer_id, cm_id, message, keyboard=None):
    try:
        params = {
            'peer_id': peer_id,
            'message': message,
            'conversation_message_id': cm_id
        }
        if keyboard: params['keyboard'] = keyboard
        return vk.messages.edit(**params)
    except Exception as e:
        print(f"Ошибка редактирования: {e}")

# --- КЛАВИАТУРЫ ---
def get_main_kb():
    return json.dumps({
        "one_time": False, 
        "buttons": [
            [{"action": {"type": "text", "label": "🎰 Казино"}, "color": "positive"},
             {"action": {"type": "text", "label": "🎲 Рулетка"}, "color": "primary"}],
            [{"action": {"type": "text", "label": "🃏 Фортуна"}, "color": "positive"},
             {"action": {"type": "text", "label": "⚔️ Дуэль"}, "color": "primary"}],
            [{"action": {"type": "text", "label": "✂️ RPS"}, "color": "primary"},
             {"action": {"type": "text", "label": "👤 Профиль"}, "color": "secondary"}],
            [{"action": {"type": "text", "label": "🚕 Такси"}, "color": "secondary"},
             {"action": {"type": "text", "label": "🎣 Рыбалка"}, "color": "secondary"},
             {"action": {"type": "text", "label": "🏹 Охота"}, "color": "secondary"}]
        ]
    }, ensure_ascii=False)

def get_activate_kb():
    return json.dumps({
        "inline": True,
        "buttons": [
            [{"action": {"type": "callback", "label": "🎮 Активировать", "payload": json.dumps({"cmd": "activate"})}, "color": "positive"}]
        ]
    }, ensure_ascii=False)

print("БОТ ЗАПУЩЕН (ПОЛНАЯ ВЕРСИЯ)!")

while True:
    try:
        for event in longpoll.listen():
            
            # 1. Приглашение в беседу
            if event.type == VkBotEventType.MESSAGE_NEW and event.object.message.get('action'):
                action = event.object.message['action']
                if action.get('type') == 'chat_invite_user' and action.get('member_id') == -GROUP_ID:
                    peer_id = event.object.message['peer_id']
                    cm_id = event.object.message.get('conversation_message_id')
                    text = "Привет! Я игровой бот.\n\nЧтобы я заработал, выдай мне администратора и нажми на кнопку ниже."
                    send_msg(peer_id, text, get_activate_kb(), reply_to=cm_id)
                    continue

            # 2. Нажатие кнопки активации
            if event.type == VkBotEventType.MESSAGE_EVENT:
                payload = event.object.payload
                peer_id = event.object.peer_id
                user_id = event.object.user_id
                event_id = event.object.event_id
                cm_id = event.object.conversation_message_id
                
                if payload.get("cmd") == "activate":
                    # Проверяем, есть ли у нажавшего права администратора
                    try:
                        members = vk.messages.getConversationMembers(peer_id=peer_id)['items']
                        is_admin = False
                        for m in members:
                            if m['member_id'] == user_id and m.get('is_admin', False):
                                is_admin = True
                                break
                        
                        if is_admin:
                            if str(peer_id) not in db["active_chats"]:
                                db["active_chats"].append(str(peer_id))
                                save_db(db)
                            vk.messages.sendMessageEventAnswer(event_id=event_id, user_id=user_id, peer_id=peer_id, event_data=json.dumps({"type": "show_snackbar", "text": "✅ Успешно!"}))
                            # РЕДАКТИРУЕМ СООБЩЕНИЕ
                            edit_msg(peer_id, cm_id, "Отлично! У бота теперь есть администратор. Чтобы пользоваться, напишите /help")
                        else:
                            vk.messages.sendMessageEventAnswer(event_id=event_id, user_id=user_id, peer_id=peer_id, event_data=json.dumps({"type": "show_snackbar", "text": "❌ Вы не администратор!"}))
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

                balance = get_balance(user_id)
                is_ls = (peer_id == user_id)

                # Если беседа и не активирована - игнорируем
                if not is_ls and str(peer_id) not in db["active_chats"]:
                    continue

                # === КОМАНДЫ В БЕСЕДЕ ===
                if not is_ls:
                    if text_lower == "/help":
                        help_text = ("📖 Команды:\n\n"
                                     "🎰 /казино [сумма]\n"
                                     "🎲 /рулетка [сумма]\n"
                                     "🃏 /фортуна [сумма]\n"
                                     "✂️ /rps [камень/ножницы/бумага] [сумма]\n"
                                     "⚔️ /duel @игрок [сумма]\n"
                                     "🚕 /такси\n"
                                     "🎣 /рыбалка\n"
                                     "🏹 /охота\n\n"
                                     "👤 /профиль\n"
                                     "🏆 /топ")
                        send_msg(peer_id, help_text, reply_to=cm_id)
                    
                    elif text_lower.startswith("/казино"):
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
                            send_msg(peer_id, "❌ Напиши: /казино [сумма].", reply_to=cm_id)
                    
                    # ... (остальные текстовые команды для беседы)
                    continue

                # === КОМАНДЫ В ЛС (ИЛИ ОБРАБОТКА КНОПОК) ===
                if text_lower in ["начать", "start", "меню"]:
                    send_msg(peer_id, f"🎰 Твой баланс: {balance} монет.\nВыбирай игру на кнопках ниже 👇", get_main_kb(), reply_to=cm_id)
                
                elif text == "🎰 Казино":
                    send_msg(peer_id, "Напиши сумму ставки для казино (например: 500):", reply_to=cm_id)
                    # В ЛС можно ловить число
                elif text == "🎲 Рулетка":
                    send_msg(peer_id, "Напиши сумму ставки для рулетки (например: 500):", reply_to=cm_id)
                elif text == "🚕 Такси":
                    earned = random.randint(50, 200)
                    set_balance(user_id, balance + earned)
                    send_msg(peer_id, f"🚕 Ты поработал в такси и заработал {earned} монет!", get_main_kb(), reply_to=cm_id)
                elif text == "🎣 Рыбалка":
                    earned = random.randint(20, 300)
                    set_balance(user_id, balance + earned)
                    send_msg(peer_id, f"🎣 Ты поймал рыбу и продал её за {earned} монет!", get_main_kb(), reply_to=cm_id)
                elif text == "🏹 Охота":
                    earned = random.randint(10, 500)
                    set_balance(user_id, balance + earned)
                    send_msg(peer_id, f"🏹 Ты удачно поохотился и заработал {earned} монет!", get_main_kb(), reply_to=cm_id)
                
                elif text == "👤 Профиль" or text_lower == "/профиль":
                    send_msg(peer_id, f"👤 Профиль:\n💰 Баланс: {balance} монет", get_main_kb(), reply_to=cm_id)
                
                elif text_lower == "/топ" or text == "🏆 Топ":
                    sorted_players = sorted(db["balances"].items(), key=lambda x: x[1], reverse=True)[:5]
                    top_text = "🏆 Топ 5 богачей:\n\n"
                    if not sorted_players: top_text += "Пока никого нет."
                    else:
                        for i, (u, b) in enumerate(sorted_players, 1):
                            top_text += f"{i}. [id{u}|Игрок] — {b} монет\n"
                    send_msg(peer_id, top_text, get_main_kb(), reply_to=cm_id)

    except Exception as e:
        print(f"⚠️ Ошибка: {e}")
        time.sleep(2)
