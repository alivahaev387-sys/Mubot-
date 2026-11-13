import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
import json, random, time, os, sqlite3, re

# ===== НАСТРОЙКИ =====
TOKEN = "vk1.a.BvMZnZvhxLsOu5bIQ1IUIIoYMEW3T88NqEAcRZ17Yj-T46O-viFXkUPWky-4XBwNZAKsWhcwqAt3TDMqQmcKva0ckucYDEUvFKa_p_LJ9ig-zNIPv7cHSZV9KP4S8XLgO0m32YWDLuqfz-rqgrrhoFKZ0mexTvf71NQ5G1JVI0H7QtuL4HGdtQkAvT7Up8xnC-vaO3QTue9x8V5a3u1-DuwMwEXIvfB4OgnVo0_FXGI"
GROUP_ID = 243089386
ADMIN_ID = 200005093141
BONUS_CD = 600 
FORTUNA_CD = 600

DATA_DIR = "/app/data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)
DB_FILE = os.path.join(DATA_DIR, "game.db")

vk_session = vk_api.VkApi(token=TOKEN, api_version='5.199')
longpoll = VkBotLongPoll(vk_session, GROUP_ID)
vk = vk_session.get_api()

print("--- БОТ ЗАПУЩЕН УСПЕШНО ---")

# ===== ИСПРАВЛЕННАЯ ФУНКЦИЯ ОТПРАВКИ (ЧЕРЕЗ vk.method) =====
def send_msg(peer_id, message, keyboard=None, reply_to=None):
    try:
        params = {
            'peer_id': peer_id, 
            'message': message, 
            'random_id': random.randint(1, 2**31 - 1),
            'group_id': GROUP_ID,
            'disable_mentions': 1 
        }
        if keyboard: 
            params['keyboard'] = keyboard
        if reply_to: 
            params['reply_to'] = int(reply_to) # ВК требует int
            
        # ИСПОЛЬЗУЕМ vk.method, ЧТОБЫ vk_api НЕ ВЫРЕЗАЛ ПАРАМЕТРЫ
        return vk.method('messages.send', params)
    except Exception as e:
        print(f"Ошибка отправки: {e}")

# ===== БАЗА ДАННЫХ =====
def get_db():
    return sqlite3.connect(DB_FILE, timeout=15, check_same_thread=False)

def init_db():
    conn = get_db(); c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, balance INTEGER DEFAULT 1000000, rep INTEGER DEFAULT 0)")
    c.execute("CREATE TABLE IF NOT EXISTS active_duels (msg_id TEXT PRIMARY KEY, challenger TEXT, bet INTEGER, peer_id TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS bonus_cd (user_id TEXT PRIMARY KEY, last_used INTEGER)")
    c.execute("CREATE TABLE IF NOT EXISTS fortune_cd (user_id TEXT PRIMARY KEY, last_used INTEGER)")
    c.execute("CREATE TABLE IF NOT EXISTS promos (code TEXT PRIMARY KEY, amount INTEGER, limit_count INTEGER, used_by TEXT DEFAULT '')")
    c.execute("CREATE TABLE IF NOT EXISTS games (game_id TEXT PRIMARY KEY, user_id TEXT, bet INTEGER, mines TEXT, opened TEXT, multiplier REAL, msg_id TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS blacklist (user_id TEXT PRIMARY KEY, reason TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS chat_messages (peer_id TEXT, user_id TEXT, count INTEGER DEFAULT 0, PRIMARY KEY (peer_id, user_id))")
    c.execute("CREATE TABLE IF NOT EXISTS activated_chats (peer_id TEXT PRIMARY KEY)")
    c.execute("CREATE TABLE IF NOT EXISTS user_businesses (user_id TEXT PRIMARY KEY, biz_id INTEGER, level INTEGER DEFAULT 1)")
    c.execute("CREATE TABLE IF NOT EXISTS rep_cooldown (user_id TEXT, target_id TEXT, last_used INTEGER, PRIMARY KEY (user_id, target_id))")
    conn.commit(); conn.close()

init_db()

def get_user(user_id):
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT balance, rep FROM users WHERE user_id = ?", (str(user_id),))
    row = c.fetchone()
    if not row:
        c.execute("INSERT INTO users (user_id) VALUES (?)", (str(user_id),))
        conn.commit()
        bal, rep = 1000000, 0
    else:
        bal, rep = row
    conn.close()
    return bal, rep

def update_balance(user_id, amount):
    bal, rep = get_user(user_id)
    conn = get_db(); c = conn.cursor()
    c.execute("UPDATE users SET balance = ? WHERE user_id = ?", (bal + amount, str(user_id)))
    conn.commit(); conn.close()

def update_rep(user_id, amount):
    bal, rep = get_user(user_id)
    conn = get_db(); c = conn.cursor()
    c.execute("UPDATE users SET rep = ? WHERE user_id = ?", (rep + amount, str(user_id)))
    conn.commit(); conn.close()

def get_name(user_id):
    try:
        u = vk.users.get(user_ids=user_id)[0]
        return f"[id{user_id}|{u['first_name']} {u['last_name']}]"
    except:
        return f"[id{user_id}|Игрок]"

def fmt(num): return f"{num:,}".replace(",", ".")

# ===== БИЗНЕСЫ =====
BIZNESSES = [
    {"id": 1, "name": "шаурмичная", "price": 500000000000, "income": 500000000, "photo": "-243089386_457239017"},
    {"id": 2, "name": "кафе", "price": 1000000000000, "income": 1000000000, "photo": "-243089386_457239018"},
    {"id": 3, "name": "большое кафе", "price": 5000000000000, "income": 7000000000, "photo": "-243089386_457239019"},
    {"id": 4, "name": "хлебопекарня", "price": 10000000000000, "income": 6000000000, "photo": "-243089386_457239020"},
    {"id": 5, "name": "ресторан", "price": 20000000000000, "income": 50000000000, "photo": "-243089386_457239021"},
    {"id": 6, "name": "отель", "price": 50000000000000, "income": 100000000000, "photo": "-243089386_457239022"},
    {"id": 7, "name": "сеть отелей", "price": 300000000000000, "income": 500000000000, "photo": "-243089386_457239023"},
    {"id": 8, "name": "казик", "price": 800000000000000, "income": 1000000000000, "photo": "-243089386_457239024"},
    {"id": 9, "name": "страна", "price": 2000000000000000, "income": 3000000000000, "photo": "-243089386_457239025"}
]

# ===== КЛАВИАТУРЫ =====
def get_main_kb():
    return json.dumps({"one_time": False, "buttons": [
        [{"action": {"type": "text", "label": "💼 Работа"}, "color": "positive"}, {"action": {"type": "text", "label": "🎰 Рулетка"}, "color": "primary"}],
        [{"action": {"type": "text", "label": "👤 Профиль"}, "color": "secondary"}, {"action": {"type": "text", "label": "🏆 Топ"}, "color": "secondary"}]]}, ensure_ascii=False)

def get_duel_kb(duel_id):
    return json.dumps({"inline": True, "buttons": [[{"action": {"type": "callback", "label": "⚔️ Сразиться", "payload": json.dumps({"cmd": "duel_accept", "duel_id": duel_id})}, "color": "positive"}]]}, ensure_ascii=False)

def get_mines_count_kb(game_id):
    kb = {"inline": True, "buttons": []}
    row = []
    for i in range(2, 9):
        row.append({"action": {"type": "callback", "label": f"{i} 💣", "payload": json.dumps({"cmd": "mines_set", "game_id": game_id, "count": i})}, "color": "secondary"})
        if len(row) == 4:
            kb["buttons"].append(row); row = []
    if row: kb["buttons"].append(row)
    return json.dumps(kb, ensure_ascii=False)

def get_mines_field_kb(game):
    kb = {"inline": True, "buttons": []}
    row = []
    for i in range(1, 10):
        if i in game["opened"]:
            row.append({"action": {"type": "callback", "label": "💥" if i in game["mines"] else "💎", "payload": "{}"}, "color": "negative" if i in game["mines"] else "positive"})
        else:
            row.append({"action": {"type": "callback", "label": str(i), "payload": json.dumps({"cmd": "mines_click", "game_id": game["id"], "cell": i})}, "color": "secondary"})
        if len(row) == 3:
            kb["buttons"].append(row); row = []
    if not game.get("is_game_over"):
        kb["buttons"].append([{"action": {"type": "callback", "label": "💰 Забрать", "payload": json.dumps({"cmd": "mines_cashout", "game_id": game["id"]})}, "color": "positive"}])
    return json.dumps(kb, ensure_ascii=False)

def get_top_msg_kb():
    return json.dumps({"inline": True, "buttons": [[{"action": {"type": "callback", "label": "💰 Топ по монетам", "payload": json.dumps({"cmd": "top_coins"})}, "color": "secondary"}]]}, ensure_ascii=False)

def get_top_coins_kb():
    return json.dumps({"inline": True, "buttons": [[{"action": {"type": "callback", "label": "🔙 Назад", "payload": json.dumps({"cmd": "top_messages"})}, "color": "secondary"}]]}, ensure_ascii=False)

def get_mafia_kb():
    return json.dumps({"inline": True, "buttons": [
        [{"action": {"type": "callback", "label": "Войти 📨", "payload": json.dumps({"cmd": "mafia_join"})}, "color": "positive"}, {"action": {"type": "callback", "label": "Выйти 📨", "payload": json.dumps({"cmd": "mafia_leave"})}, "color": "negative"}],
        [{"action": {"type": "callback", "label": "🚀 Начать игру", "payload": json.dumps({"cmd": "mafia_start"})}, "color": "primary"}, {"action": {"type": "callback", "label": "❌ Отмена", "payload": json.dumps({"cmd": "mafia_cancel"})}, "color": "secondary"}],
        [{"action": {"type": "open_link", "label": "✉️ Написать боту", "link": f"https://vk.com/write-{GROUP_ID}"}}]
    ]}, ensure_ascii=False)

def get_biz_kb():
    kb = {"inline": True, "buttons": []}
    row = []
    for b in BIZNESSES:
        row.append({"action": {"type": "callback", "label": b["name"], "payload": json.dumps({"cmd": f"buy_biz_{b['id']}"})}, "color": "positive"})
        if len(row) == 2:
            kb["buttons"].append(row); row = []
    if row: kb["buttons"].append(row)
    return json.dumps(kb, ensure_ascii=False)

def get_my_biz_kb():
    return json.dumps({"inline": True, "buttons": [
        [{"action": {"type": "callback", "label": "Вывести $$$", "payload": json.dumps({"cmd": "biz_collect"})}, "color": "positive"}],
        [{"action": {"type": "callback", "label": "Повысить уровень", "payload": json.dumps({"cmd": "biz_upgrade"})}, "color": "primary"}],
        [{"action": {"type": "callback", "label": "Закрыть бизнес", "payload": json.dumps({"cmd": "biz_close"})}, "color": "negative"}]
    ]}, ensure_ascii=False)

# ===== ОСНОВНОЙ ЦИКЛ =====
while True:
    try:
        for event in longpoll.listen():
            
            # --- ОБРАБОТКА КНОПОК ---
            if event.type == VkBotEventType.MESSAGE_EVENT:
                payload = event.object.payload
                peer_id, user_id, event_id, cm_id = event.object.peer_id, event.object.user_id, event.object.event_id, event.object.conversation_message_id
                
                # Бизнесы
                if "cmd" in payload and payload["cmd"].startswith("buy_biz_"):
                    biz_id = int(payload["cmd"].split("_")[2])
                    biz = next((b for b in BIZNESSES if b["id"] == biz_id), None)
                    conn = get_db(); c = conn.cursor()
                    c.execute("SELECT biz_id FROM user_businesses WHERE user_id = ?", (str(user_id),))
                    if c.fetchone():
                        vk.messages.sendMessageEventAnswer(event_id=event_id, user_id=user_id, peer_id=peer_id, event_data=json.dumps({"type": "show_snackbar", "text": "❌ У вас уже есть бизнес!"}))
                        conn.close(); continue
                    
                    bal, _ = get_user(user_id)
                    if bal < biz["price"]:
                        vk.messages.sendMessageEventAnswer(event_id=event_id, user_id=user_id, peer_id=peer_id, event_data=json.dumps({"type": "show_snackbar", "text": "❌ Недостаточно денег!"}))
                        conn.close(); continue
                    
                    update_balance(user_id, -biz["price"])
                    c.execute("INSERT INTO user_businesses (user_id, biz_id) VALUES (?, ?)", (str(user_id), biz_id))
                    conn.commit(); conn.close()
                    vk.messages.sendMessageEventAnswer(event_id=event_id, user_id=user_id, peer_id=peer_id, event_data=json.dumps({"type": "show_snackbar", "text": f"✅ Вы купили {biz['name']}!"}))
                    continue

                if payload.get("cmd") == "biz_collect":
                    conn = get_db(); c = conn.cursor()
                    c.execute("SELECT biz_id, level FROM user_businesses WHERE user_id = ?", (str(user_id),))
                    row = c.fetchone()
                    if row:
                        biz = next((b for b in BIZNESSES if b["id"] == row[0]), None)
                        income = biz["income"] * row[1]
                        update_balance(user_id, income)
                        vk.messages.sendMessageEventAnswer(event_id=event_id, user_id=user_id, peer_id=peer_id, event_data=json.dumps({"type": "show_snackbar", "text": f"💰 Выведено: {fmt(income)}$"}))
                    else:
                        vk.messages.sendMessageEventAnswer(event_id=event_id, user_id=user_id, peer_id=peer_id, event_data=json.dumps({"type": "show_snackbar", "text": "❌ У вас нет бизнеса."}))
                    conn.close(); continue

                if payload.get("cmd") == "biz_upgrade":
                    conn = get_db(); c = conn.cursor()
                    c.execute("SELECT biz_id, level FROM user_businesses WHERE user_id = ?", (str(user_id),))
                    row = c.fetchone()
                    if row:
                        if row[1] >= 5:
                            vk.messages.sendMessageEventAnswer(event_id=event_id, user_id=user_id, peer_id=peer_id, event_data=json.dumps({"type": "show_snackbar", "text": "❌ Максимальный уровень!"}))
                            conn.close(); continue
                        biz = next((b for b in BIZNESSES if b["id"] == row[0]), None)
                        cost = biz["price"] * row[1]
                        bal, _ = get_user(user_id)
                        if bal < cost:
                            vk.messages.sendMessageEventAnswer(event_id=event_id, user_id=user_id, peer_id=peer_id, event_data=json.dumps({"type": "show_snackbar", "text": "❌ Не хватает денег!"}))
                            conn.close(); continue
                        update_balance(user_id, -cost)
                        c.execute("UPDATE user_businesses SET level = level + 1 WHERE user_id = ?", (str(user_id),))
                        conn.commit()
                        vk.messages.sendMessageEventAnswer(event_id=event_id, user_id=user_id, peer_id=peer_id, event_data=json.dumps({"type": "show_snackbar", "text": f"✅ Уровень повышен до {row[1] + 1}!"}))
                    conn.close(); continue

                if payload.get("cmd") == "biz_close":
                    conn = get_db(); c = conn.cursor()
                    c.execute("SELECT biz_id FROM user_businesses WHERE user_id = ?", (str(user_id),))
                    row = c.fetchone()
                    if row:
                        biz = next((b for b in BIZNESSES if b["id"] == row[0]), None)
                        refund = int(biz["price"] * 0.5)
                        update_balance(user_id, refund)
                        c.execute("DELETE FROM user_businesses WHERE user_id = ?", (str(user_id),))
                        conn.commit()
                        vk.messages.sendMessageEventAnswer(event_id=event_id, user_id=user_id, peer_id=peer_id, event_data=json.dumps({"type": "show_snackbar", "text": f"✅ Бизнес закрыт. Возврат: {fmt(refund)}$"}))
                    else:
                        vk.messages.sendMessageEventAnswer(event_id=event_id, user_id=user_id, peer_id=peer_id, event_data=json.dumps({"type": "show_snackbar", "text": "❌ У вас нет бизнеса."}))
                    conn.close(); continue

                # Мафия
                if payload.get("cmd") == "mafia_join":
                    try:
                        send_msg(user_id, "✅ Вы вошли в игру Мафия!")
                        vk.messages.sendMessageEventAnswer(event_id=event_id, user_id=user_id, peer_id=peer_id, event_data=json.dumps({"type": "show_snackbar", "text": "✅ Вы вошли в игру!"}))
                    except:
                        vk.messages.sendMessageEventAnswer(event_id=event_id, user_id=user_id, peer_id=peer_id, event_data=json.dumps({"type": "show_snackbar", "text": "⚠️ Напишите боту в ЛС! (Кнопка внизу)"}))
                    continue
                if payload.get("cmd") == "mafia_start":
                    vk.messages.sendMessageEventAnswer(event_id=event_id, user_id=user_id, peer_id=peer_id, event_data=json.dumps({"type": "show_snackbar", "text": "🚀 Игра началась! Роли в ЛС."}))
                    continue
                if payload.get("cmd") == "mafia_cancel":
                    vk.messages.sendMessageEventAnswer(event_id=event_id, user_id=user_id, peer_id=peer_id, event_data=json.dumps({"type": "show_snackbar", "text": "❌ Игра отменена."}))
                    continue

                # Топы
                if payload.get("cmd") == "top_coins":
                    conn = get_db(); c = conn.cursor()
                    c.execute("SELECT user_id, balance FROM users ORDER BY balance DESC LIMIT 10")
                    rows = c.fetchall(); conn.close()
                    text = "🏆 Топ 10 богачей:\n\n"
                    for i, r in enumerate(rows, 1):
                        text += f"{i}. {get_name(r[0])} — {fmt(r[1])}$\n"
                    vk.messages.edit(peer_id=peer_id, message=text, conversation_message_id=cm_id, keyboard=get_top_coins_kb())
                    vk.messages.sendMessageEventAnswer(event_id=event_id, user_id=user_id, peer_id=peer_id, event_data=json.dumps({"type": "show_snackbar", "text": "Загружено"}))
                    continue

                if payload.get("cmd") == "top_messages":
                    conn = get_db(); c = conn.cursor()
                    c.execute("SELECT user_id, count FROM chat_messages WHERE peer_id = ? ORDER BY count DESC LIMIT 10", (str(peer_id),))
                    rows = c.fetchall(); conn.close()
                    text = "⭐ ТОП 10 ПО СООБЩЕНИЯМ\n\n"
                    emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
                    for i, r in enumerate(rows):
                        text += f"{emojis[i]} {get_name(r[0])} - {r[1]} сообщений\n"
                    vk.messages.edit(peer_id=peer_id, message=text, conversation_message_id=cm_id, keyboard=get_top_msg_kb())
                    vk.messages.sendMessageEventAnswer(event_id=event_id, user_id=user_id, peer_id=peer_id, event_data=json.dumps({"type": "show_snackbar", "text": "Загружено"}))
                    continue

                # Мины
                if payload.get("cmd") == "mines_set":
                    game_id, count = payload["game_id"], payload["count"]
                    conn = get_db(); c = conn.cursor()
                    c.execute("SELECT bet FROM games WHERE game_id = ? AND user_id = ?", (game_id, str(user_id)))
                    row = c.fetchone()
                    if row:
                        mines = json.dumps(random.sample(range(1, 10), count))
                        c.execute("UPDATE games SET mines = ?, opened = '[]', multiplier = 1.0 WHERE game_id = ?", (mines, game_id))
                        conn.commit()
                        game = {"id": game_id, "opened": [], "mines": json.loads(mines)}
                        vk.messages.edit(peer_id=peer_id, message=f"💣 Мины\nСтавка: {row[0]}$ | Мин: {count}\nВыбирай клетку:", conversation_message_id=cm_id, keyboard=get_mines_field_kb(game))
                        vk.messages.sendMessageEventAnswer(event_id=event_id, user_id=user_id, peer_id=peer_id, event_data=json.dumps({"type": "show_snackbar", "text": "Игра началась!"}))
                    conn.close(); continue
                
                if payload.get("cmd") == "mines_click":
                    game_id, cell = payload["game_id"], payload["cell"]
                    conn = get_db(); c = conn.cursor()
                    c.execute("SELECT bet, mines, opened, multiplier FROM games WHERE game_id = ? AND user_id = ?", (game_id, str(user_id)))
                    row = c.fetchone()
                    if row:
                        bet, mines_str, opened_str, mult = row
                        mines, opened = json.loads(mines_str), json.loads(opened_str)
                        if cell in opened: conn.close(); continue
                        opened.append(cell)
                        
                        if cell in mines:
                            update_balance(user_id, -bet)
                            c.execute("DELETE FROM games WHERE game_id = ?", (game_id,))
                            conn.commit()
                            game = {"id": game_id, "opened": list(range(1, 10)), "mines": mines, "is_game_over": True}
                            vk.messages.edit(peer_id=peer_id, message=f"💥 Вы подорвались!\nПроигрыш: -{bet}$", conversation_message_id=cm_id, keyboard=get_mines_field_kb(game))
                            vk.messages.sendMessageEventAnswer(event_id=event_id, user_id=user_id, peer_id=peer_id, event_data=json.dumps({"type": "show_snackbar", "text": "💥 БУМ!"}))
                            conn.close(); continue
                        
                        new_mult = 1.0
                        for i in range(len(opened)):
                            new_mult *= (9 - i) / (9 - len(mines) - i)
                        new_mult = round(new_mult * 0.95, 2)
                        c.execute("UPDATE games SET opened = ?, multiplier = ? WHERE game_id = ?", (json.dumps(opened), new_mult, game_id))
                        conn.commit()
                        game = {"id": game_id, "opened": opened, "mines": mines}
                        vk.messages.edit(peer_id=peer_id, message=f"💣 Мины\nКоэф: x{new_mult}\nВыигрыш: {int(bet * new_mult)}$", conversation_message_id=cm_id, keyboard=get_mines_field_kb(game))
                        vk.messages.sendMessageEventAnswer(event_id=event_id, user_id=user_id, peer_id=peer_id, event_data=json.dumps({"type": "show_snackbar", "text": f"💎 x{new_mult}"}))
                    conn.close(); continue

                if payload.get("cmd") == "mines_cashout":
                    game_id = payload["game_id"]
                    conn = get_db(); c = conn.cursor()
                    c.execute("SELECT bet, multiplier FROM games WHERE game_id = ? AND user_id = ?", (game_id, str(user_id)))
                    row = c.fetchone()
                    if row:
                        win = int(row[0] * row[1])
                        update_balance(user_id, win)
                        c.execute("DELETE FROM games WHERE game_id = ?", (game_id,))
                        conn.commit()
                        vk.messages.edit(peer_id=peer_id, message=f"💰 Вы забрали {win}$!", conversation_message_id=cm_id, keyboard=json.dumps({"buttons":[]}))
                        vk.messages.sendMessageEventAnswer(event_id=event_id, user_id=user_id, peer_id=peer_id, event_data=json.dumps({"type": "show_snackbar", "text": f"💰 Забрано: {win}$"}))
                    conn.close(); continue

            # --- ОБРАБОТКА СООБЩЕНИЙ ---
            if event.type == VkBotEventType.MESSAGE_NEW:
                msg = event.object.message
                user_id = msg['from_id']
                peer_id = msg['peer_id']
                text = msg.get('text', '').strip().lower()
                is_ls = (peer_id == user_id)

                # Приветствие
                if 'action' in msg and msg['action']:
                    action = msg['action']
                    if action.get('type') in ['chat_invite_user', 'chat_invite_user_by_link']:
                        if str(action.get('member_id')) == str(-GROUP_ID):
                            send_msg(peer_id, "👋 Добро пожаловать! Я официальный игровой бот Game Zone.\n\nДля активации выдайте мне права администратора и напишите /start")
                            continue

                if not text: continue

                # Счетчик
                if not is_ls:
                    conn = get_db(); c = conn.cursor()
                    c.execute("SELECT count FROM chat_messages WHERE peer_id = ? AND user_id = ?", (str(peer_id), str(user_id)))
                    if c.fetchone():
                        c.execute("UPDATE chat_messages SET count = count + 1 WHERE peer_id = ? AND user_id = ?", (str(peer_id), str(user_id)))
                    else:
                        c.execute("INSERT INTO chat_messages (peer_id, user_id, count) VALUES (?, ?, 1)", (str(peer_id), str(user_id)))
                    conn.commit(); conn.close()

                # ЧС
                if text.startswith('/'):
                    conn = get_db(); c = conn.cursor()
                    c.execute("SELECT reason FROM blacklist WHERE user_id = ?", (str(user_id),))
                    row = c.fetchone(); conn.close()
                    if row:
                        send_msg(peer_id, f"🚫 Вы в ЧС. Причина: {row[0]}", reply_to=msg['id'])
                        continue

                if not text.startswith('/') and text != '💼 работа': continue

                clean_text = text.replace("/", "").strip()
                parts = clean_text.split()
                balance, rep = get_user(user_id)

                # === КОМАНДЫ ===
                if text in ["начать", "start"]:
                    if is_ls:
                        send_msg(peer_id, "👋 Привет! Я бот.", keyboard=get_main_kb(), reply_to=msg['id'])
                    else:
                        conn = get_db(); c = conn.cursor()
                        c.execute("SELECT peer_id FROM activated_chats WHERE peer_id = ?", (str(peer_id),))
                        if c.fetchone():
                            send_msg(peer_id, "✅ Бот уже активирован! Напиши /help.", reply_to=msg['id'])
                        else:
                            try:
                                members = vk.messages.getConversationMembers(peer_id=peer_id)
                                is_user_admin = any(m['member_id'] == user_id and m.get('is_admin') for m in members['items'])
                                is_bot_admin = any(m['member_id'] == -GROUP_ID and m.get('is_admin') for m in members['items'])
                                
                                if not is_user_admin:
                                    send_msg(peer_id, "❌ У вас нет прав администратора.", reply_to=msg['id'])
                                elif not is_bot_admin:
                                    send_msg(peer_id, "❌ Выдайте боту права администратора.", reply_to=msg['id'])
                                else:
                                    c.execute("INSERT INTO activated_chats (peer_id) VALUES (?)", (str(peer_id),))
                                    conn.commit()
                                    send_msg(peer_id, "✅ Бот успешно активирован! Напишите /help.", reply_to=msg['id'])
                            except:
                                send_msg(peer_id, "⚠️ Ошибка проверки прав.", reply_to=msg['id'])
                        conn.close()
                    continue

                if clean_text in ["help", "помощь", "команды"]:
                    help_txt = "📖 Доступные команды:\n\n🎰 /рулетка [цвет/чет] [ставка]\n🎲 /фортуна (100$)\n💣 /мины [ставка]\n⚔️ /duel [сумма]\n💸 /transfer [сумма] (ответом)\n🎁 /бонус\n🎁 /promo [код]\n📜 /промолист\n🕵️ /мафия (Игра в беседе)\n📊 /rep + / (Репутация)\n🏢 /бизнес\n👤 /профиль\n🏆 /топ"
                    send_msg(peer_id, help_txt, keyboard=get_main_kb() if is_ls else None, reply_to=msg['id'])
                    continue

                if text == "💼 работа":
                    earned = random.randint(100, 500)
                    update_balance(user_id, earned)
                    send_msg(peer_id, f"✅ Заработано {earned}$!", keyboard=get_main_kb(), reply_to=msg['id'])
                    continue

                if clean_text in ["профиль", "баланс"]:
                    send_msg(peer_id, f"👤 Профиль:\n💰 Баланс: {fmt(balance)}$\n📊 Репутация: {rep}\n🆔 ID: {user_id}", keyboard=get_main_kb() if is_ls else None, reply_to=msg['id'])
                    continue

                if clean_text in ["топ", "top"]:
                    if is_ls:
                        send_msg(peer_id, "❌ Только в беседах!", reply_to=msg['id'])
                        continue
                    conn = get_db(); c = conn.cursor()
                    c.execute("SELECT user_id, count FROM chat_messages WHERE peer_id = ? ORDER BY count DESC LIMIT 10", (str(peer_id),))
                    rows = c.fetchall(); conn.close()
                    if not rows:
                        send_msg(peer_id, "🏆 Пусто.", reply_to=msg['id'])
                        continue
                    top_txt = "⭐ ТОП 10 ПО СООБЩЕНИЯМ\n\n"
                    emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
                    for i, r in enumerate(rows):
                        top_txt += f"{emojis[i]} {get_name(r[0])} - {r[1]} сообщений\n"
                    send_msg(peer_id, top_txt, keyboard=get_top_msg_kb(), reply_to=msg['id'])
                    continue

                if clean_text.startswith('rep'):
                    sign = parts[1] if len(parts) > 1 else None
                    if not sign or ("+" not in sign and "-" not in sign):
                        send_msg(peer_id, "❌ Формат: /rep + @user", reply_to=msg['id'])
                        continue
                    target_id = None
                    if 'reply_message' in msg:
                        target_id = msg['reply_message']['from_id']
                    else:
                        match = re.search(r'\[id(\d+)\|', msg['text']) or re.search(r'@id(\d+)', msg['text'])
                        if match: target_id = int(match.group(1))
                    
                    if not target_id:
                        send_msg(peer_id, "❌ Ответьте или укажите @.", reply_to=msg['id'])
                        continue
                    if target_id == user_id:
                        send_msg(peer_id, "❌ Себе нельзя.", reply_to=msg['id'])
                        continue

                    conn = get_db(); c = conn.cursor()
                    c.execute("SELECT last_used FROM rep_cooldown WHERE user_id = ? AND target_id = ?", (str(user_id), str(target_id)))
                    cd = c.fetchone()
                    if cd and time.time() - cd[0] < 86400:
                        send_msg(peer_id, "⏳ Вы уже меняли репутацию сегодня.", reply_to=msg['id'])
                        conn.close(); continue

                    amount = 1 if '+' in sign else -1
                    update_rep(target_id, amount)
                    c.execute("REPLACE INTO rep_cooldown (user_id, target_id, last_used) VALUES (?, ?, ?)", (str(user_id), str(target_id), int(time.time())))
                    conn.commit(); conn.close()
                    send_msg(peer_id, f"✅ Вы изменили репутацию {get_name(target_id)} на {amount}", reply_to=msg['id'])
                    continue

                # Бизнесы
                if clean_text == 'бизнес':
                    conn = get_db(); c = conn.cursor()
                    c.execute("SELECT biz_id FROM user_businesses WHERE user_id = ?", (str(user_id),))
                    if c.fetchone():
                        send_msg(peer_id, "❌ У вас уже есть бизнес! Напишите /мой_бизнес.", reply_to=msg['id'])
                    else:
                        elements = []
                        for b in BIZNESSES:
                            elements.append({
                                "title": b["name"],
                                "description": f"цена: {fmt(b['price'])}$\nзаработок: {fmt(b['income'])}$/час",
                                "photo_id": b["photo"],
                                "action": {"type": "open_photo"},
                                "buttons": [{"action": {"type": "callback", "label": "Купить", "payload": json.dumps({"cmd": f"buy_biz_{b['id']}"})}, "color": "positive"}]
                            })
                        template = json.dumps({"type": "carousel", "elements": elements})
                        try:
                            vk.messages.send(peer_id=peer_id, message="🏪 Магазин бизнесов 👉", template=template, random_id=random.randint(1, 2**31))
                        except:
                            send_msg(peer_id, "🏪 Выберите бизнес:", keyboard=get_biz_kb(), reply_to=msg['id'])
                    conn.close(); continue

                if clean_text == 'мой_бизнес':
                    conn = get_db(); c = conn.cursor()
                    c.execute("SELECT biz_id, level FROM user_businesses WHERE user_id = ?", (str(user_id),))
                    row = c.fetchone(); conn.close()
                    if not row:
                        send_msg(peer_id, "❌ Нет бизнеса. Напишите /бизнес.", reply_to=msg['id'])
                    else:
                        b = next((x for x in BIZNESSES if x["id"] == row[0]), None)
                        send_msg(peer_id, f"🏢 {b['name']}\n💪 Уровень: {row[1]}/5\n😼 {fmt(b['income'] * row[1])}$/час", keyboard=get_my_biz_kb(), reply_to=msg['id'])
                    continue

                # Мафия
                if clean_text == 'мафия':
                    if is_ls:
                        send_msg(peer_id, "❌ Только в беседах.", reply_to=msg['id'])
                        continue
                    host = get_name(user_id)
                    send_msg(peer_id, f"🎭 МАФИЯ — регистрация\n\n👑 Ведущий: {host}\n\nНужно минимум 4 игрока. Роли придут в ЛС!", keyboard=get_mafia_kb(), reply_to=msg['id'])
                    continue

                # Рулетка
                if clean_text.startswith('рулетка') or clean_text.startswith('рул'):
                    if len(parts) >= 3:
                        choice = parts[1]
                        bet_str = parts[-1]
                        bet = balance if bet_str in ["вб", "всё", "все"] else int(bet_str) if bet_str.isdigit() else 0
                        if bet < 10 or bet > balance:
                            send_msg(peer_id, f"❌ Мин. 10, у тебя {fmt(balance)}$", reply_to=msg['id'])
                            continue
                        res = random.randint(0, 36)
                        red = [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]
                        win = (choice.isdigit() and int(choice) == res) or (choice in ["красное", "кр"] and res in red) or (choice in ["черное", "чр"] and res not in red and res != 0) or (choice in ["чет"] and res % 2 == 0 and res != 0) or (choice in ["нечет"] and res % 2 != 0)
                        if win:
                            update_balance(user_id, bet)
                            send_msg(peer_id, f"🎰 Выпало: {res}. Выигрыш: +{bet}$", reply_to=msg['id'])
                        else:
                            update_balance(user_id, -bet)
                            send_msg(peer_id, f"🎰 Выпало: {res}. Проигрыш: -{bet}$", reply_to=msg['id'])
                    else:
                        send_msg(peer_id, "❌ Формат: /рулетка красное 500", reply_to=msg['id'])
                    continue

                if clean_text == 'фортуна':
                    conn = get_db(); c = conn.cursor()
                    c.execute("SELECT last_used FROM fortune_cd WHERE user_id = ?", (str(user_id),))
                    row = c.fetchone()
                    if row and time.time() - row[0] < FORTUNA_CD:
                        send_msg(peer_id, "⏳ Ждите.", reply_to=msg['id'])
                        conn.close(); continue
                    if balance < 100:
                        send_msg(peer_id, "❌ Стоит 100$.", reply_to=msg['id'])
                        conn.close(); continue
                    update_balance(user_id, -100)
                    c.execute("REPLACE INTO fortune_cd (user_id, last_used) VALUES (?, ?)", (str(user_id), int(time.time())))
                    conn.commit(); conn.close()
                    prize = random.choice([0, 50, 100, 200, 500, 1000, 5000])
                    update_balance(user_id, prize)
                    send_msg(peer_id, f"🎰 Выпало: {fmt(prize)}$!", reply_to=msg['id'])
                    continue

                if clean_text.startswith('мины'):
                    bet = 100
                    if len(parts) >= 2 and parts[1].isdigit(): bet = int(parts[1])
                    if bet < 10 or bet > balance:
                        send_msg(peer_id, "❌ Мин. 10", reply_to=msg['id'])
                        continue
                    game_id = str(random.randint(10000, 99999))
                    conn = get_db(); c = conn.cursor()
                    c.execute("INSERT INTO games (game_id, user_id, bet, mines, opened, multiplier, msg_id) VALUES (?, ?, ?, '[]', '[]', 1.0, ?)", (game_id, str(user_id), bet, str(msg['id'])))
                    conn.commit(); conn.close()
                    send_msg(peer_id, f"💣 Мины\nСтавка: {bet}$\nВыберите кол-во мин:", keyboard=get_mines_count_kb(game_id), reply_to=msg['id'])
                    continue

                if clean_text == 'бонус':
                    conn = get_db(); c = conn.cursor()
                    c.execute("SELECT last_used FROM bonus_cd WHERE user_id = ?", (str(user_id),))
                    row = c.fetchone()
                    if row and time.time() - row[0] < BONUS_CD:
                        send_msg(peer_id, "⏳ Ждите.", reply_to=msg['id'])
                        conn.close(); continue
                    amount = random.choice([100000, 200000, 500000])
                    update_balance(user_id, amount)
                    c.execute("REPLACE INTO bonus_cd (user_id, last_used) VALUES (?, ?)", (str(user_id), int(time.time())))
                    conn.commit(); conn.close()
                    send_msg(peer_id, f"🎁 Бонус: +{fmt(amount)}$", reply_to=msg['id'])
                    continue

                # ===== АДМИНКА =====
                if user_id == ADMIN_ID:
                    if clean_text.startswith('kick'):
                        target_id = msg['reply_message']['from_id'] if 'reply_message' in msg else None
                        if target_id and not is_ls:
                            try:
                                vk.messages.removeChatUser(chat_id=peer_id-2000000000, user_id=target_id, group_id=GROUP_ID)
                                send_msg(peer_id, "✅ Исключен.", reply_to=msg['id'])
                            except:
                                send_msg(peer_id, "⚠️ Ошибка.", reply_to=msg['id'])
                        else:
                            send_msg(peer_id, "⚠️ Ответьте на сообщение.", reply_to=msg['id'])
                        continue
                        
                    if clean_text.startswith('чсб'):
                        target_id = msg['reply_message']['from_id'] if 'reply_message' in msg else None
                        if target_id:
                            reason = " ".join(parts[1:]) or "Без причины"
                            conn = get_db(); c = conn.cursor()
                            c.execute("REPLACE INTO blacklist (user_id, reason) VALUES (?, ?)", (str(target_id), reason))
                            conn.commit(); conn.close()
                            send_msg(peer_id, f"✅ Пользователь в ЧС.", reply_to=msg['id'])
                        else:
                            send_msg(peer_id, "⚠️ Ответьте на сообщение.", reply_to=msg['id'])
                        continue
                        
                    if clean_text.startswith('деньги'):
                        target_id = None
                        if 'reply_message' in msg:
                            target_id = msg['reply_message']['from_id']
                        else:
                            match = re.search(r'\[id(\d+)\|', msg['text']) or re.search(r'@id(\d+)', msg['text'])
                            if match: target_id = int(match.group(1))
                        
                        if len(parts) >= 2 and parts[1].isdigit() and target_id:
                            amount = int(parts[1])
                            update_balance(target_id, amount)
                            send_msg(peer_id, f"✅ Выдано {fmt(amount)}$ игроку {get_name(target_id)}", reply_to=msg['id'])
                        else:
                            send_msg(peer_id, "❌ Формат: /деньги [сумма] (ответом ИЛИ с @упоминанием)", reply_to=msg['id'])
                        continue
                        
                    if clean_text.startswith('создать'):
                        if len(parts) == 4 and parts[2].isdigit() and parts[3].isdigit():
                            conn = get_db(); c = conn.cursor()
                            c.execute("REPLACE INTO promos (code, amount, limit_count, used_by) VALUES (?, ?, ?, '')", (parts[1], int(parts[2]), int(parts[3])))
                            conn.commit(); conn.close()
                            send_msg(peer_id, f"✅ Промокод {parts[1]} создан на {parts[2]}$", reply_to=msg['id'])
                        else:
                            send_msg(peer_id, "❌ Формат: /создать [код] [сумма] [лимит]", reply_to=msg['id'])
                        continue
                        
                    if clean_text == 'cp':
                        conn = get_db(); c = conn.cursor()
                        c.execute("DELETE FROM promos")
                        conn.commit(); conn.close()
                        send_msg(peer_id, "✅ Все промокоды удалены.", reply_to=msg['id'])
                        continue

                if clean_text == 'промолист':
                    conn = get_db(); c = conn.cursor()
                    c.execute("SELECT code, amount FROM promos")
                    rows = c.fetchall(); conn.close()
                    if not rows:
                        send_msg(peer_id, "❌ Пусто.", reply_to=msg['id'])
                    else:
                        txt = "🎁 Промокоды:\n\n" + "\n".join([f"▪️ {r[0]} — {r[1]}$" for r in rows])
                        send_msg(peer_id, txt, reply_to=msg['id'])
                    continue

                if clean_text.startswith('promo'):
                    if len(parts) == 2:
                        conn = get_db(); c = conn.cursor()
                        c.execute("SELECT amount, limit_count, used_by FROM promos WHERE code = ?", (parts[1],))
                        row = c.fetchone()
                        if not row:
                            send_msg(peer_id, "❌ Неверный код.", reply_to=msg['id'])
                            conn.close(); continue
                        amount, limit, used_by_str = row
                        used_by = used_by_str.split(",") if used_by_str else []
                        if str(user_id) in used_by:
                            send_msg(peer_id, "❌ Вы уже активировали.", reply_to=msg['id'])
                            conn.close(); continue
                        used_by.append(str(user_id))
                        c.execute("UPDATE promos SET used_by = ? WHERE code = ?", (",".join(used_by), parts[1]))
                        conn.commit()
                        update_balance(user_id, amount)
                        send_msg(peer_id, f"✅ Активирован! +{amount}$", reply_to=msg['id'])
                        conn.close()
                    continue

    except Exception as e:
        print(f"⚠️ Ошибка в цикле: {e}")
        time.sleep(1)
