import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
import json, random, sqlite3, time

# ===== ТОКЕН И НАСТРОЙКИ =====
TOKEN = "vk1.a.NsWXdLrl8pBiaoFvBKvb8gjeJKElZWRNovKhQtZhtXsMRE1XoEKF0E6PqGjWuySsdg46zbklbV99ksp8Wkt_wpFPVeDs2UWN7-AmmeOGMfUbDcMS9BgnayD5DKfGKOSZRimPlFPOVxfPfSzonZLgtp_pHhVNqsnf50va4C-gWG7xnzkD6nX6YJDlDhj5k0oa5cciIsdp8o7Z__SdsUMkp9WcOrPfjcleQbMnaH7pk68"
GROUP_ID = 242296265 

vk_session = vk_api.VkApi(token=TOKEN)
longpoll = VkBotLongPoll(vk_session, GROUP_ID)
vk = vk_session.get_api()

# Состояния для ставок
waiting_for_bet = {} 
waiting_for_amount = {} 

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
            [{"action": {"type": "text", "label": "🎰 Казино"}, "color": "positive"},
             {"action": {"type": "text", "label": "👤 Профиль"}, "color": "primary"}],
            [{"action": {"type": "text", "label": "🏆 Топ игроков"}, "color": "secondary"},
             {"action": {"type": "text", "label": "📖 Помощь"}, "color": "negative"}]
        ]
    }, ensure_ascii=False)

def get_casino_kb():
    return json.dumps({
        "one_time": False, 
        "buttons": [
            [{"action": {"type": "text", "label": "🔴 Красное / ⚫ Черное"}, "color": "primary"},
             {"action": {"type": "text", "label": "🟢 Чет / 🔴 Нечет"}, "color": "primary"}],
            [{"action": {"type": "text", "label": "⬅️ Назад"}, "color": "secondary"}]
        ]
    }, ensure_ascii=False)

def get_bet_kb():
    return json.dumps({
        "one_time": False, 
        "buttons": [
            [{"action": {"type": "text", "label": "100"}, "color": "secondary"},
             {"action": {"type": "text", "label": "500"}, "color": "secondary"},
             {"action": {"type": "text", "label": "1000"}, "color": "secondary"}],
            [{"action": {"type": "text", "label": "Всё!"}, "color": "positive"}],
            [{"action": {"type": "text", "label": "⬅️ Отмена"}, "color": "negative"}]
        ]
    }, ensure_ascii=False)

# ===== ЗАПУСК =====
print("КАЗИНО БОТ ЗАПУЩЕН!")

while True:
    try:
        for event in longpoll.listen():
            if event.type == VkBotEventType.MESSAGE_NEW and event.object.message['peer_id']:
                msg = event.object.message
                peer_id = msg['peer_id']
                user_id = msg['from_id'] 
                msg_id = msg.get('id')
                
                text = msg.get('text', '').strip().lower().replace("@club242296265", "")
                
                if peer_id != user_id: continue

                balance, xp, wins = get_player(user_id)

                # === БЛОК 1: ОЖИДАНИЕ СУММЫ СТАВКИ ===
                if user_id in waiting_for_amount:
                    game_type = waiting_for_amount[user_id]
                    del waiting_for_amount[user_id] 
                    
                    bet_amount = 0
                    if text == "всё!":
                        bet_amount = balance
                    else:
                        try:
                            bet_amount = int(text)
                        except ValueError:
                            send_msg(peer_id, "❌ Введи число (сумму ставки) или нажми кнопку.", get_bet_kb(), reply_to=msg_id)
                            continue

                    if bet_amount < 10:
                        send_msg(peer_id, "❌ Минимальная ставка — 10 монет.", get_main_kb(), reply_to=msg_id)
                        continue
                    if bet_amount > balance:
                        send_msg(peer_id, f"❌ У тебя нет столько денег! Баланс: {balance}", get_main_kb(), reply_to=msg_id)
                        continue

                    waiting_for_bet[user_id] = {"type": game_type, "bet": bet_amount}
                    
                    if game_type == "color":
                        msg_text = f"💰 Ставка: {bet_amount} монет.\n\nВыбирай цвет:"
                        kb = json.dumps({"inline": True, "buttons": [
                            [{"action": {"type": "callback", "label": "🔴 Красное (x2)", "payload": json.dumps({"cmd": "spin", "choice": "red"})}, "color": "negative"},
                             {"action": {"type": "callback", "label": "⚫ Черное (x2)", "payload": json.dumps({"cmd": "spin", "choice": "black"})}, "color": "secondary"}]
                        ]}, ensure_ascii=False)
                        send_msg(peer_id, msg_text, kb, reply_to=msg_id)
                    elif game_type == "parity":
                        msg_text = f"💰 Ставка: {bet_amount} монет.\n\nВыбирай четность:"
                        kb = json.dumps({"inline": True, "buttons": [
                            [{"action": {"type": "callback", "label": "🟢 Чет (x2)", "payload": json.dumps({"cmd": "spin", "choice": "even"})}, "color": "positive"},
                             {"action": {"type": "callback", "label": "🔴 Нечет (x2)", "payload": json.dumps({"cmd": "spin", "choice": "odd"})}, "color": "negative"}]
                        ]}, ensure_ascii=False)
                        send_msg(peer_id, msg_text, kb, reply_to=msg_id)
                    continue

                # === БЛОК 2: ОБРАБОТКА ИНЛАЙН-КНОПОК (СПИН) ===
                if event.type == VkBotEventType.MESSAGE_EVENT:
                    payload = event.object.payload
                    cmd = payload.get("cmd")
                    
                    if cmd == "spin":
                        if user_id not in waiting_for_bet:
                            vk.messages.sendMessageEventAnswer(event_id=event.object.event_id, user_id=user_id, peer_id=peer_id, event_data=json.dumps({"type": "show_snackbar", "text": "❌ Ставка не найдена или устарела."}))
                            continue
                        
                        choice = payload.get("choice")
                        bet_data = waiting_for_bet[user_id]
                        bet_amount = bet_data["bet"]
                        game_type = bet_data["type"]
                        del waiting_for_bet[user_id] 
                        
                        vk.messages.sendMessageEventAnswer(event_id=event.object.event_id, user_id=user_id, peer_id=peer_id, event_data=json.dumps({"type": "show_snackbar", "text": "🎲 Крутим рулетку..."}))
                        time.sleep(1)
                        
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
                        continue

                # === БЛОК 3: ТЕКСТОВЫЕ КОМАНДЫ ===
                if text in ["начать", "start", "меню"]:
                    send_msg(peer_id, "🎰 Добро пожаловать в Казино!\nТвой баланс: " + str(balance) + " монет.", get_main_kb(), reply_to=msg_id)
                
                elif "казино" in text or "🎰" in text:
                    send_msg(peer_id, "🎰 Выбери игру:", get_casino_kb(), reply_to=msg_id)
                
                elif "красное" in text or "черное" in text:
                    waiting_for_amount[user_id] = "color"
                    send_msg(peer_id, f"🔴⚫ Выбрана игра Цвета.\n\nНапиши сумму ставки (у тебя {balance}):", get_bet_kb(), reply_to=msg_id)
                
                elif "чет" in text or "нечет" in text:
                    waiting_for_amount[user_id] = "parity"
                    send_msg(peer_id, f"🟢🔴 Выбрана игра Чет/Нечет.\n\nНапиши сумму ставки (у тебя {balance}):", get_bet_kb(), reply_to=msg_id)
                
                elif "профиль" in text or "👤" in text:
                    status = "🥉 Новичок" if xp < 100 else "🥈 Опытный" if xp < 500 else "🥇 Мастер" if xp < 2000 else "💎 Хайроллер"
                    send_msg(peer_id, f"👤 Профиль:\n💰 Баланс: {balance} монет\n⭐ Опыт: {xp} XP\n🏆 Побед: {wins}\n\nТвой статус: {status}", get_main_kb(), reply_to=msg_id)
                
                elif "топ" in text or "🏆" in text:
                    conn = sqlite3.connect('casino.db')
                    c = conn.cursor()
                    c.execute("SELECT user_id, balance FROM players ORDER BY balance DESC LIMIT 5")
                    top = c.fetchall()
                    conn.close()
                    top_text = "🏆 Топ 5 богачей:\n\n"
                    for i, (u, b) in enumerate(top, 1):
                        top_text += f"{i}. [id{u}|Игрок] — {b} монет\n"
                    send_msg(peer_id, top_text, get_main_kb(), reply_to=msg_id)
                
                elif "помощь" in text or "📖" in text:
                    send_msg(peer_id, "📖 Правила казино:\n\n🔴 Красное / ⚫ Черное — угадай цвет, выигрыш x2.\n🟢 Чет / 🔴 Нечет — угадай четность, выигрыш x2.\n\n⚠️ Если выпадает ЗЕРО (0) — выигрывает казино.\nМинимальная ставка: 10 монет.", get_main_kb(), reply_to=msg_id)
                
                elif "назад" in text:
                    send_msg(peer_id, "Главное меню:", get_main_kb(), reply_to=msg_id)

                else:
                    send_msg(peer_id, "Выбери действие на кнопках 👇", get_main_kb(), reply_to=msg_id)

    except Exception as e:
        print(f"⚠️ Ошибка (перезапуск): {e}")
        time.sleep(2)
