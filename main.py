import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
import json, random, sqlite3, time

# ===== ТОКЕН И НАСТРОЙКИ =====
TOKEN = "vk1.a.Fgowv-iH2wbOXG7ra56zmUWabQJy2OBRma9n4V3ufueJ_FJrbt5K_t9dOu_OtC-xF1iTWBi8yX5bGOmQ1kbQExof1U4IZKgoO6NVGNg9aaR17ECXar65GK6s-LdkflKto0qhZddvXHeDhxkFeya3z5XN80QnNGB7F676pFOs4xScHkUyvyvodMk5QsFpDHSrJ45m23CVzidcr1reHfrqW5ci9FxMDEhiF3JGG1021qQ"
GROUP_ID = 243089386
ADMIN_ID = 200005093141 # Твой ID для уведомлений

vk_session = vk_api.VkApi(token=TOKEN)
longpoll = VkBotLongPoll(vk_session, GROUP_ID)
vk = vk_session.get_api()

# Состояния
waiting_for_bet = {} 
active_chats = set() # Активные беседы

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect('casino.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS players 
                 (user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 1000, xp INTEGER DEFAULT 0, wins INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

def get_player(user_id):
    conn = sqlite3.connect('casino.db')
    c = conn.cursor()
    c.execute("SELECT balance, xp, wins FROM players WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    if not row:
        c.execute("INSERT INTO players (user_id, balance, xp, wins) VALUES (?, 1000, 0, 0)", (user_id,))
        conn.commit()
        row = (1000, 0, 0)
    conn.close()
    return row

def update_player(user_id, coin_change, xp_change, win_change=0):
    conn = sqlite3.connect('casino.db')
    c = conn.cursor()
    c.execute("UPDATE players SET balance = balance + ?, xp = xp + ?, wins = wins + ? WHERE user_id = ?", 
              (coin_change, xp_change, win_change, user_id))
    conn.commit()
    conn.close()

init_db()

# --- ОТПРАВКА СООБЩЕНИЙ (С РЕПЛАЕМ) ---
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
        print(f"Ошибка: {e}")

# --- КЛАВИАТУРЫ ---
def get_main_kb():
    return json.dumps({
        "one_time": False, 
        "buttons": [
            [{"action": {"type": "text", "label": "👤 Профиль"}, "color": "primary"},
             {"action": {"type": "text", "label": "🏆 Топ игроков"}, "color": "secondary"}],
            [{"action": {"type": "text", "label": "📖 Помощь"}, "color": "negative"}]
        ]
    }, ensure_ascii=False)

# Кнопка активации для беседы
def get_activate_kb():
    return json.dumps({
        "one_time": False, 
        "buttons": [
            [{"action": {"type": "text", "label": "🎮 Активировать бота"}, "color": "positive"}]
        ]
    }, ensure_ascii=False)

# ===== ЗАПУСК =====
print("ИГРОВОЙ БОТ ЗАПУЩЕН (С РЕЖИМОМ БЕСЕД)!")

while True:
    try:
        for event in longpoll.listen():
            
            # === ОБРАБОТКА ДОБАВЛЕНИЯ В БЕСЕДУ ===
            if event.type == VkBotEventType.MESSAGE_NEW and event.object.message.get('action'):
                action = event.object.message['action']
                if action.get('type') == 'chat_invite_user' and action.get('member_id') == -GROUP_ID:
                    peer_id = event.object.message['peer_id']
                    
                    # Бот добавлен. Отправляем приветствие.
                    text = ("Привет! Я игровой бот.\n\n"
                            "Чтобы я работал, выдай мне права администратора беседы и нажми на кнопку ниже.")
                    send_msg(peer_id, text, keyboard=get_activate_kb())
                    continue

            # === ОБРАБОТКА СООБЩЕНИЙ ===
            if event.type == VkBotEventType.MESSAGE_NEW and event.object.message['text']:
                msg = event.object.message
                peer_id = msg['peer_id']
                user_id = msg['from_id'] 
                msg_id = msg.get('id')
                text = msg.get('text', '').strip().lower()
                
                is_chat = peer_id > 2000000000

                # === АКТИВАЦИЯ БОТА В БЕСЕДЕ ===
                if is_chat and (text == "🎮 активировать бота" or text == "активировать бота"):
                    # Проверяем, есть ли у бота права админа
                    try:
                        admins = vk.messages.getConversationMembers(peer_id=peer_id)['items']
                        bot_rights = None
                        for a in admins:
                            if a['member_id'] == -GROUP_ID:
                                bot_rights = a.get('is_admin', False)
                                break
                        
                        if not bot_rights:
                            send_msg(peer_id, "Ошибка: у бота нету администратора. Выдайте боту права администратора беседы.", reply_to=msg_id)
                            continue
                            
                    except Exception as e:
                        send_msg(peer_id, "Ошибка: не удалось проверить права.", reply_to=msg_id)
                        continue

                    # Проверяем, является ли нажавший админом
                    try:
                        admins = vk.messages.getConversationMembers(peer_id=peer_id)['items']
                        is_user_admin = False
                        for a in admins:
                            if a['member_id'] == user_id and a.get('is_admin', False):
                                is_user_admin = True
                                break
                        
                        if not is_user_admin:
                            send_msg(peer_id, "Ошибка: вы не являетесь администратором беседы.", reply_to=msg_id)
                            continue
                            
                    except Exception as e:
                        send_msg(peer_id, "Ошибка: не удалось проверить ваши права.", reply_to=msg_id)
                        continue

                    # Если всё ок — активируем
                    active_chats.add(peer_id)
                    send_msg(peer_id, "✅ Бот успешно активирован в беседе!\nТеперь тут работают игровые команды (/help).", keyboard=get_main_kb(), reply_to=msg_id)
                    continue

                # === ИГРОВЫЕ КОМАНДЫ ===
                # Работаем только в ЛС или в активированных беседах
                if is_chat and peer_id not in active_chats:
                    continue # Игнорируем беседы, где бот не активирован

                balance, xp, wins = get_player(user_id)

                # Ожидание ставки
                if user_id in waiting_for_bet:
                    game_data = waiting_for_bet[user_id]
                    game_type = game_data["game"]
                    choice = game_data.get("choice", None)
                    
                    if text in ["отмена", "назад"]:
                        del waiting_for_bet[user_id]
                        send_msg(peer_id, "Ставка отменена.", get_main_kb(), reply_to=msg_id)
                        continue
                        
                    try:
                        if text in ["всё", "все", "all"]:
                            bet_amount = balance
                        else:
                            bet_amount = int(text)
                    except ValueError:
                        send_msg(peer_id, "❌ Введи число (сумму ставки) или напиши 'всё'.", reply_to=msg_id)
                        continue

                    if bet_amount < 10:
                        send_msg(peer_id, "❌ Минимальная ставка — 10 монет.", reply_to=msg_id)
                        continue
                    if bet_amount > balance:
                        send_msg(peer_id, f"❌ У тебя нет столько денег! Баланс: {balance}", reply_to=msg_id)
                        continue

                    del waiting_for_bet[user_id]
                    
                    if game_type in ["color", "parity"]:
                        result_num = random.randint(0, 36)
                        is_even = (result_num % 2 == 0) and result_num != 0
                        is_red = result_num in [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]
                        
                        color_emoji = "🔴" if is_red else ("⚫" if result_num != 0 else "🟢")
                        num_text = "ЗЕРО (0)" if result_num == 0 else f"{result_num} {color_emoji}"
                        
                        win = False
                        if game_type == "color":
                            if choice == "red" and is_red: win = True
                            if choice == "black" and not is_red and result_num != 0: win = True
                        elif game_type == "parity":
                            if choice == "even" and is_even: win = True
                            if choice == "odd" and not is_even and result_num != 0: win = True
                                
                        if win:
                            update_player(user_id, bet_amount, 15, 1)
                            res_text = f"🎉 ПОБЕДА!\n\nВыпало: {num_text}\nТы выиграл {bet_amount} монет!"
                        else:
                            update_player(user_id, -bet_amount, 5, 0)
                            res_text = f"😔 ПРОИГРЫШ!\n\nВыпало: {num_text}\nТы потерял {bet_amount} монет."
                        send_msg(peer_id, res_text, get_main_kb(), reply_to=msg_id)

                    elif game_type == "drim":
                        result_num = random.randint(1, 15)
                        if result_num == choice:
                            update_player(user_id, bet_amount * 10, 50, 1)
                            res_text = f"🔥 ДЖЕКПОТ! 🔥\n\nВыпало число: {result_num}\nТы выиграл x10: +{bet_amount * 10} монет!"
                        else:
                            update_player(user_id, -bet_amount, 5, 0)
                            res_text = f"😔 ПРОИГРЫШ!\n\nВыпало число: {result_num}\nТы потерял {bet_amount} монет."
                        send_msg(peer_id, res_text, get_main_kb(), reply_to=msg_id)
                    
                    elif game_type == "rps":
                        bot_choice = random.choice(["камень", "ножницы", "бумага"])
                        win = False
                        draw = False
                        if choice == bot_choice: draw = True
                        elif (choice == "камень" and bot_choice == "ножницы") or \
                             (choice == "ножницы" and bot_choice == "бумага") or \
                             (choice == "бумага" and bot_choice == "камень"): win = True
                             
                        if draw:
                            res_text = f"🤝 НИЧЬЯ!\n\nТы: {choice}\nБот: {bot_choice}\nТвои монеты возвращаются."
                        elif win:
                            update_player(user_id, bet_amount, 15, 1)
                            res_text = f"🎉 ПОБЕДА!\n\nТы: {choice}\nБот: {bot_choice}\nТы выиграл {bet_amount} монет!"
                        else:
                            update_player(user_id, -bet_amount, 5, 0)
                            res_text = f"😔 ПРОИГРЫШ!\n\nТы: {choice}\nБот: {bot_choice}\nТы потерял {bet_amount} монет."
                        send_msg(peer_id, res_text, get_main_kb(), reply_to=msg_id)
                    continue

                # Основные команды
                if text == "/help" or text == "помощь":
                    help_text = ("📖 Доступные команды:\n\n"
                                 "🎰 /казино — меню игр\n"
                                 "🔴 /красное или /черное (x2)\n"
                                 "🟢 /чет или /нечет (x2)\n"
                                 "🔢 /дрим [1-15] (x10)\n"
                                 "✂️ /rps [камень/ножницы/бумага]\n"
                                 "⚔️ /duel @игрок [сумма]\n\n"
                                 "👤 /профиль\n"
                                 "🏆 /топ")
                    send_msg(peer_id, help_text, get_main_kb(), reply_to=msg_id)
                
                elif text in ["начать", "start", "меню"]:
                    send_msg(peer_id, "🎰 Твой баланс: " + str(balance) + " монет.\nВведи /help для списка команд.", get_main_kb(), reply_to=msg_id)
                
                elif text == "/казино":
                    send_msg(peer_id, "🎰 Игры:\n/красное\n/черное\n/чет\n/нечет\n/дрим [1-15]\n/rps [камень/ножницы/бумага]", get_main_kb(), reply_to=msg_id)
                
                elif text == "/красное":
                    waiting_for_bet[user_id] = {"game": "color", "choice": "red"}
                    send_msg(peer_id, "🔴 Выбрано Красное. Напиши сумму ставки:", reply_to=msg_id)
                elif text == "/черное":
                    waiting_for_bet[user_id] = {"game": "color", "choice": "black"}
                    send_msg(peer_id, "⚫ Выбрано Черное. Напиши сумму ставки:", reply_to=msg_id)
                elif text == "/чет":
                    waiting_for_bet[user_id] = {"game": "parity", "choice": "even"}
                    send_msg(peer_id, "🟢 Выбран Чет. Напиши сумму ставки:", reply_to=msg_id)
                elif text == "/нечет":
                    waiting_for_bet[user_id] = {"game": "parity", "choice": "odd"}
                    send_msg(peer_id, "🔴 Выбран Нечет. Напиши сумму ставки:", reply_to=msg_id)
                elif text.startswith("/дрим"):
                    parts = text.split()
                    if len(parts) == 2 and parts[1].isdigit() and 1 <= int(parts[1]) <= 15:
                        waiting_for_bet[user_id] = {"game": "drim", "choice": int(parts[1])}
                        send_msg(peer_id, f"🔢 Выбрано число {parts[1]}. Напиши сумму ставки:", reply_to=msg_id)
                    else:
                        send_msg(peer_id, "❌ Напиши: /дрим 7 (от 1 до 15).", reply_to=msg_id)
                elif text.startswith("/rps"):
                    parts = text.split()
                    if len(parts) == 2 and parts[1] in ["камень", "ножницы", "бумага"]:
                        waiting_for_bet[user_id] = {"game": "rps", "choice": parts[1]}
                        send_msg(peer_id, f"✂️ Ты выбрал: {parts[1]}. Напиши сумму ставки:", reply_to=msg_id)
                    else:
                        send_msg(peer_id, "❌ Напиши: /rps камень (или ножницы, бумага).", reply_to=msg_id)
                elif text.startswith("/duel"):
                    parts = text.split()
                    if len(parts) == 3 and (parts[1].startswith("[id") or parts[1].startswith("@")):
                        target = parts[1].replace("[id", "").replace("|", "").replace("]", "")
                        try:
                            amount = int(parts[2])
                            if amount > 0 and amount <= balance:
                                if amount < 10:
                                    send_msg(peer_id, "❌ Мин. перевод 10 монет.", reply_to=msg_id)
                                else:
                                    update_player(user_id, -amount, 0)
                                    update_player(int(target), amount, 0)
                                    send_msg(peer_id, f"✅ Ты перевел {amount} монет игроку {parts[1]}!", reply_to=msg_id)
                            else:
                                send_msg(peer_id, "❌ Недостаточно монет.", reply_to=msg_id)
                        except:
                            send_msg(peer_id, "❌ Напиши: /duel @id123456 500", reply_to=msg_id)
                    else:
                        send_msg(peer_id, "❌ Напиши: /duel @id123456 500", reply_to=msg_id)
                elif "профиль" in text or "/профиль" in text:
                    status = "🥉 Новичок" if xp < 100 else "🥈 Опытный" if xp < 500 else "🥇 Мастер" if xp < 2000 else "💎 Хайроллер"
                    send_msg(peer_id, f"👤 Профиль:\n💰 Баланс: {balance}\n⭐ Опыт: {xp} XP\n🏆 Побед: {wins}\nСтатус: {status}", get_main_kb(), reply_to=msg_id)
                elif "топ" in text or "/топ" in text:
                    conn = sqlite3.connect('casino.db')
                    c = conn.cursor()
                    c.execute("SELECT user_id, balance FROM players ORDER BY balance DESC LIMIT 5")
                    top = c.fetchall()
                    conn.close()
                    top_text = "🏆 Топ 5 богачей:\n\n"
                    for i, (u, b) in enumerate(top, 1):
                        top_text += f"{i}. [id{u}|Игрок] — {b} монет\n"
                    send_msg(peer_id, top_text, get_main_kb(), reply_to=msg_id)
                elif not is_chat:
                    send_msg(peer_id, "Неизвестная команда. Напиши /help.", get_main_kb(), reply_to=msg_id)

    except Exception as e:
        print(f"⚠️ Ошибка: {e}")
        time.sleep(2)
