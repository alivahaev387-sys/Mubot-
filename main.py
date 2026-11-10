import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
import json, random, time, asyncio, os
import sqlite3

# ===== НАСТРОЙКИ =====
TOKEN = "vk1.a.n-y1VnQMFI87cAGH7zXHwYy6LncLM_UuAaCihe6dlWxUBLGwS8no-KjRmFrA9zmwy-STfP7f2VZOHArq1-WVKYVRUA3H1F3-pO5gtXRxEziw3u3st-dTYHNiK_an2ZcbUIpXYNy98HHTGQv12wFtMLsSASQ0kO0ke0B0DRsXc7hn-LQrYcpbu54a_kQmP7dxBO5a8gTmuS9Dn9LH7oMLfE6G6_GPJZxJAgkwzptCnWw"
GROUP_ID = 243089386
ADMIN_ID = 200005093141 
FORTUNA_CD = 600
BONUS_CD = 600 

DATA_DIR = "/app/data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)
DB_FILE = os.path.join(DATA_DIR, "game.db")

vk_session = vk_api.VkApi(token=TOKEN)
longpoll = VkBotLongPoll(vk_session, GROUP_ID)
vk = vk_session.get_api()

# ===== БАЗА ДАННЫХ =====
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, balance INTEGER DEFAULT 1000)")
    c.execute("CREATE TABLE IF NOT EXISTS promos (code TEXT PRIMARY KEY, amount INTEGER, limit_count INTEGER, used_by TEXT DEFAULT '')")
    c.execute("CREATE TABLE IF NOT EXISTS fortune_cd (user_id TEXT PRIMARY KEY, last_used INTEGER)")
    c.execute("CREATE TABLE IF NOT EXISTS bonus_cd (user_id TEXT PRIMARY KEY, last_used INTEGER)")
    c.execute("CREATE TABLE IF NOT EXISTS games (game_id TEXT PRIMARY KEY, user_id TEXT, bet INTEGER, mines TEXT, opened TEXT, multiplier REAL)")
    c.execute("CREATE TABLE IF NOT EXISTS active_duels (msg_id TEXT PRIMARY KEY, challenger TEXT, bet INTEGER, peer_id TEXT)")
    conn.commit()
    conn.close()

def get_balance(user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE user_id = ?", (str(user_id),))
    row = c.fetchone()
    if not row:
        c.execute("INSERT INTO users (user_id, balance) VALUES (?, 1000)", (str(user_id),))
        conn.commit()
        bal = 1000
    else:
        bal = row[0]
    conn.close()
    return bal

def update_balance(user_id, amount):
    bal = get_balance(user_id)
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE users SET balance = ? WHERE user_id = ?", (bal + amount, str(user_id)))
    conn.commit()
    conn.close()

# ФУНКЦИЯ ПОЛУЧЕНИЯ ИМЕНИ (БЕЗ ТЕГОВ)
def get_user_name(user_id):
    try:
        user_info = vk.users.get(user_ids=user_id)[0]
        return f"{user_info['first_name']} {user_info['last_name']}"
    except:
        return f"Игрок {user_id}"

def send_msg(peer_id, message, keyboard=None, reply_to=None):
    try:
      
                    c = conn.cursor()
                    c.execute("SELECT bet FROM games WHERE game_id = ? AND user_id = ?", (game_id, str(user_id)))
                    row = c.fetchone()
                    if row:
                        bet = row[0]
                        mines = json.dumps(random.sample(range(1, 10), mine_count))
                        c.execute("UPDATE games SET mines = ?, opened = '[]', multiplier = 1.0 WHERE game_id = ?", (mines, game_id))
                        conn.commit()
                        
                        game = {"id": game_id, "opened": [], "mines": json.loads(mines)}
                        msg_text = f"💣 Мины\nСтавка: {bet}$ | Мин: {mine_count} из 9\n\nВыбери клетку, чтобы открыть алмаз 💎"
                        edit_msg(peer_id, cm_id, msg_text, get_mines_field_kb(game))
                        vk.messages.sendMessageEventAnswer(event_id=event_id, user_id=user_id, peer_id=peer_id, event_data=json.dumps({"type": "show_snackbar", "text": "Игра началась!"}))
                    conn.close()
                
                elif payload.get("cmd") == "mines_click":
                    game_id, cell = payload["game_id"], payload["cell"]
                    conn = sqlite3.connect(DB_FILE)
                    c = conn.cursor()
                    c.execute("SELECT bet, mines, opened, multiplier FROM games WHERE game_id = ? AND user_id = ?", (game_id, str(user_id)))
                    row = c.fetchone()
                    if row:
                        bet, mines_str, opened_str, mult = row
                        mines = json.loads(mines_str)
                        opened = json.loads(opened_str)
                        
                        if cell in opened: conn.close(); continue
                        opened.append(cell)
                        
                        if cell in mines:
                            update_balance(user_id, -bet)
                            c.execute("DELETE FROM games WHERE game_id = ?", (game_id,))
                            conn.commit()
                            game = {"id": game_id, "opened": list(range(1, 10)), "mines": mines}
                            msg_text = f"💥 Вы попали на мину!\n\nПроигрыш: -{bet}$\nБаланс: {get_balance(user_id)}$"
                            edit_msg(peer_id, cm_id, msg_text, get_mines_field_kb(game))
                            vk.messages.sendMessageEventAnswer(event_id=event_id, user_id=user_id, peer_id=peer_id, event_data=json.dumps({"type": "show_snackbar", "text": "💥 БУМ! Вы проиграли."}))
                            conn.close(); continue
                        
                        opened_count, mines_count = len(opened), len(mines)
                        new_mult = 1.0
                        for i in range(opened_count):
                            new_mult *= (9 - i) / (9 - mines_count - i)
                        new_mult = round(new_mult * 0.95, 2)
                        
                        c.execute("UPDATE games SET opened = ?, multiplier = ? WHERE game_id = ?", (json.dumps(opened), new_mult, game_id))
                        conn.commit()
                        
                        win_amount = int(bet * new_mult)
                        game = {"id": game_id, "opened": opened, "mines": mines}
                        msg_text = (f"💣 Мины\nСтавка: {bet}$ | Мин: {mines_count} из 9\n\n"
                                    f"Открыто алмазов: {opened_count} | Коэф: x{new_mult}\n"
                                    f"Выигрыш сейчас: {win_amount}$\nСледующий алмаз даст больше!")
                        edit_msg(peer_id, cm_id, msg_text, get_mines_field_kb(game))
                        vk.messages.sendMessageEventAnswer(event_id=event_id, user_id=user_id, peer_id=peer_id, event_data=json.dumps({"type": "show_snackbar", "text": f"💎 Алмаз! x{new_mult}"}))
                    conn.close()
                
                elif payload.get("cmd") == "mines_cashout":
                    game_id = payload["game_id"]
                    conn = sqlite3.connect(DB_FILE)
                    c = conn.cursor()
                    c.execute("SELECT bet, multiplier FROM games WHERE game_id = ? AND user_id = ?", (game_id, str(user_id)))
                    row = c.fetchone()
                    if row:
                        bet, mult = row
                        win_amount = int(bet * mult)
                        update_balance(user_id, win_amount)
                        c.execute("DELETE FROM games WHERE game_id = ?", (game_id,))
                        conn.commit()
                        msg_text = f"💰 Вы забрали выигрыш: {win_amount}$!\nБаланс: {get_balance(user_id)}$"
                        edit_msg(peer_id, cm_id, msg_text, None)
                        vk.messages.sendMessageEventAnswer(event_id=event_id, user_id=user_id, peer_id=peer_id, event_data=json.dumps({"type": "show_snackbar", "text": "💰 Деньги у вас!"}))
                    conn.close()
                continue

            if event.type == VkBotEventType.MESSAGE_NEW:
                msg = event.object.message
                user_id, peer_id = msg['from_id'], msg['peer_id']
                text = msg.get('text', '').strip().lower()
                is_ls = (peer_id == user_id)
                
                get_balance(user_id)
                
                clean_text = text.replace("/", "").strip()
                parts = clean_text.split()
                
                reply_to_id = msg.get('id') if not is_ls else None

                if not text and is_ls:
                    send_msg(peer_id, f"👋 Привет! Твой баланс: {get_balance(user_id)}$\nЖми «Работа» или пиши /help", get_main_kb()); continue
                if not text: continue

                if clean_text in ["help", "помощь", "команды"]:
                    help_text = (
                        "📖 **Игровые команды:**\n\n"
                        "🎰 /рулетка [цвет/чет] [ставка]\n"
                        "🎲 /фортуна - Крутить (100$)\n"
                        "💣 /мины [ставка] - Открывай алмазы\n"
                        "🎁 /бонус - Получить бонус (раз в 10 мин)\n"
                        "✂️ /rps [фигура] [ставка]\n"
                        "⚔️ /duel [сумма] - Вызов (реплай)\n"
                        "👤 /профиль - Твой баланс (можно реплаем)\n"
                        "🏆 /топ - Богачи\n"
                        "🎁 /promo [код] - Активировать\n"
                        "📜 /промолист - Список активных кодов"
                    )
                    send_msg(peer_id, help_text, keyboard=get_main_kb() if is_ls else None, reply_to=reply_to_id); continue

                elif clean_text == "бонус":
                    uid = str(user_id)
                    current_time = int(time.time())
                    
                    conn = sqlite3.connect(DB_FILE)
                    c = conn.cursor()
                    c.execute("SELECT last_used FROM bonus_cd WHERE user_id = ?", (uid,))
                    row = c.fetchone()
                    last_use = row[0] if row else 0
                    
                    if current_time - last_use < BONUS_CD:
                        remaining = BONUS_CD - (current_time - last_use)
                        msg = f"⏳ Следующий бонус будет доступен через {remaining // 60} мин. {remaining % 60} сек."
                        send_msg(peer_id, msg, reply_to=reply_to_id); conn.close(); continue
                        
                    bonus_amount = random.choice([1000000, 1500000, 2000000, 2500000, 3000000])
                    update_balance(user_id, bonus_amount)
                    
                    c.execute("REPLACE INTO bonus_cd (user_id, last_used) VALUES (?, ?)", (uid, current_time))
                    conn.commit()
                    conn.close()
                    
                    msg = (
                        f"🎁 Бонус получен! ✨ VIP\n"
                        f"+{bonus_amount:,}$\n".replace(",", ".") +
                        f"+5 exp\n\n"
                        f"💰 Баланс: {get_balance(user_id):,}$\n".replace(",", ".") +
                        f"Следующий бонус — через 10 минут."
                    )
                    send_msg(peer_id, msg, reply_to=reply_to_id)
                    continue

                if is_ls:
                    if clean_text in ["начать", "start", "меню", "привет"]:
                        send_msg(peer_id, f"🎰 Твой баланс: {get_balance(user_id)}$\nЖми кнопку или пиши /help", get_main_kb())
                    elif text == "💼 работа": send_msg(peer_id, "Выбери работу:", get_work_kb())
                    elif text == "🔙 назад": send_msg(peer_id, "Меню:", get_main_kb())
                    elif text in ["🚕 такси", "🎣 рыбалка", "🏹 охота"]:
                        earned = random.randint(200, 800); update_balance(user_id, earned)
                        send_msg(peer_id, f"✅ Ты заработал {earned}$!\n💰 Баланс: {get_balance(user_id)}$", get_work_kb())

                elif clean_text.startswith("duel"):
                    if len(parts) == 2 and parts[1].isdigit():
                        bet = int(parts[1])
                        if bet < 50 or bet > 2000:
                            send_msg(peer_id, "❌ Ставка должна быть от 50 до 2000 монет.", reply_to=reply_to_id)
                            continue
                            
                        if get_balance(user_id) < bet:
                            send_msg(peer_id, "❌ У тебя не хватает монет для этой дуэли.", reply_to=reply_to_id)
                            continue

                        duel_id = str(random.randint(10000, 99999))
                        
                        conn = sqlite3.connect(DB_FILE)
                        c = conn.cursor()
                        c.execute("REPLACE INTO active_duels (msg_id, challenger, bet, peer_id) VALUES (?, ?, ?, ?)", (duel_id, str(user_id), bet, str(peer_id)))
                        conn.commit()
                        conn.close()
                        
                        duel_text = (
                            f"⚔️ Дуэль на монеты!\n"
                            f"👤 Создатель: {get_user_name(user_id)}\n"
                            f"💰 Ставка: {bet} монет\n\n"
                            f"🌑 Приз: {int(bet*1.8)} монет победителю\n"
                            f"⚡ Нажмите \"Сразиться\", чтобы сразиться!!"
                        )
                        send_msg(peer_id, duel_text, get_duel_kb(duel_id), reply_to=reply_to_id)
                    else:
                        send_msg(peer_id, "❌ Формат: /duel [сумма] (от 50 до 2000)", reply_to=reply_to_id)

                elif clean_text.startswith("kick") and user_id == ADMIN_ID and not is_ls:
                    target_id = None
                    if msg.get('reply_message'):
                        target_id = msg['reply_message']['from_id']
                    
                    if target_id:
                        if target_id == user_id:
                            send_msg(peer_id, "❌ Ты не можешь кикнуть сам себя.", reply_to=reply_to_id)
                        else:
                            try:
                                vk.messages.removeChatUser(chat_id=peer_id - 2000000000, user_id=target_id)
                                send_msg(peer_id, f"👢 Игрок {get_user_name(target_id)} был кикнут из беседы.", reply_to=reply_to_id)
                            except Exception as e:
                                err_text = str(e).lower()
                                if "no access" in err_text or "access denied" in err_text or "not enough" in err_text:
                                    send_msg(peer_id, f"⚠️ Я не могу кикнуть {get_user_name(target_id)}, потому что у меня нет прав администратора в этой беседе. Выдай мне админку!", reply_to=reply_to_id)
                                else:
                                    send_msg(peer_id, f"❌ Ошибка при кике: {e}", reply_to=reply_to_id)
                    else:
                        send_msg(peer_id, "❌ Чтобы кикнуть, ответь (реплаем) на сообщение игрока и напиши /kick", reply_to=reply_to_id)

                elif clean_text.startswith("рулетка") or clean_text.startswith("рул"):
                    if len(parts) >= 3:
                        await process_roulette(user_id, peer_id, parts[1], parts[-1], reply_to=reply_to_id, is_ls=is_ls)
                    else: send_msg(peer_id, "❌ Формат: /рулетка красное 500", reply_to=reply_to_id)
                
                elif clean_text.startswith("фортуна"):
                    await process_fortune(user_id, peer_id, reply_to=reply_to_id, is_ls=is_ls)
                
                elif clean_text.startswith("мины"):
                    if len(parts) >= 2:
                        bet_str = parts[1]
                        bet = get_balance(user_id) if bet_str in ["все", "вб", "всё"] else int(bet_str) if bet_str.isdigit() else int(bet_str[:-1]) * 1000 if bet_str.endswith("к") and bet_str[:-1].isdigit() else 0
                        if bet < 10 or bet > get_balance(user_id): send_msg(peer_id, f"❌ Мин. ставка 10, у тебя {get_balance(user_id)}$", reply_to=reply_to_id); continue
                        
                        game_id = str(random.randint(10000, 99999))
                        conn = sqlite3.connect(DB_FILE)
                        c = conn.cursor()
                        c.execute("INSERT INTO games (game_id, user_id, bet, mines, opened, multiplier) VALUES (?, ?, ?, '[]', '[]', 1.0)", (game_id, str(user_id), bet))
                        conn.commit()
                        conn.close()
                        send_msg(peer_id, f"💣 Мины\nСтавка: {bet}$\n\nВыберите количество мин (2-8):", get_mines_count_kb(game_id), reply_to=reply_to_id)
                    else: send_msg(peer_id, "❌ Формат: /мины 500", reply_to=reply_to_id)

                elif clean_text.startswith("rps"):
                    if len(parts) == 3 and parts[2].isdigit():
                        bet, p_choice = int(par
