import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
import json, random, time, os
import sqlite3

# ===== НАСТРОЙКИ =====
TOKEN = "vk1.a.n-y1VnQMFI87cAGH7zXHwYy6LncLM_UuAaCihe6dlWxUBLGwS8no-KjRmFrA9zmwy-STfP7f2VZOHArq1-WVKYVRUA3H1F3-pO5gtXRxEziw3u3st-dTYHNiK_an2ZcbUIpXYNy98HHTGQv12wFtMLsSASQ0kO0ke0B0DRsXc7hn-LQrYcpbu54a_kQmP7dxBO5a8gTmuS9Dn9LH7oMLfE6G6_GPJZxJAgkwzptCnWw"
GROUP_ID = 243089386
ADMIN_ID = 200005093141 
BONUS_CD = 600 

DATA_DIR = "/app/data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)
DB_FILE = os.path.join(DATA_DIR, "game.db")

# Версия 5.131 для реплаев
vk_session = vk_api.VkApi(token=TOKEN, api_version='5.131')
longpoll = VkBotLongPoll(vk_session, GROUP_ID)
vk = vk_session.get_api()

print("--- БОТ ЗАПУЩЕН УСПЕШНО ---")

# ===== БАЗА ДАННЫХ =====
def get_db():
    return sqlite3.connect(DB_FILE, timeout=15, check_same_thread=False)

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, balance INTEGER DEFAULT 1000)")
    c.execute("CREATE TABLE IF NOT EXISTS active_duels (msg_id TEXT PRIMARY KEY, challenger TEXT, bet INTEGER, peer_id TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS bonus_cd (user_id TEXT PRIMARY KEY, last_used INTEGER)")
    c.execute("CREATE TABLE IF NOT EXISTS promos (code TEXT PRIMARY KEY, amount INTEGER, limit_count INTEGER, used_by TEXT DEFAULT '')")
    conn.commit()
    conn.close()

def get_balance(user_id):
    try:
        conn = get_db()
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
    except:
        return 1000

def update_balance(user_id, amount):
    try:
        bal = get_balance(user_id)
        conn = get_db()
        c = conn.cursor()
        c.execute("UPDATE users SET balance = ? WHERE user_id = ?", (bal + amount, str(user_id)))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"DB Error: {e}")

def get_user_name(user_id):
    try:
        user_info = vk.users.get(user_ids=user_id)[0]
        return f"[id{user_id}|{user_info['first_name']}]"
    except:
        return f"[id{user_id}|Игрок]"

# ===== ОТПРАВКА С ЖЕСТКИМ РЕПЛАЕМ =====
def send_msg(peer_id, message, keyboard=None, reply_to=None):
    try:
        params = {
            'peer_id': peer_id, 
            'message': message, 
            'random_id': random.randint(1, 2**31 - 1),
            'group_id': GROUP_ID, 
            'v': '5.131'
        }
        if keyboard: params['keyboard'] = keyboard
        if reply_to: 
            params['reply_to'] = int(reply_to)
            
        params['disable_mentions'] = 1 
        return vk.method('messages.send', params)
    except Exception as e:
        print(f"Ошибка отправки: {e}")

# ===== КЛАВИАТУРЫ =====
def get_main_kb():
    return json.dumps({"one_time": False, "buttons": [
        [{"action": {"type": "text", "label": "💼 Работа"}, "color": "positive"}, {"action": {"type": "text", "label": "🎰 Рулетка"}, "color": "primary"}],
        [{"action": {"type": "text", "label": "👤 Профиль"}, "color": "secondary"}, {"action": {"type": "text", "label": "🏆 Топ"}, "color": "secondary"}]]}, ensure_ascii=False)

def get_duel_kb(duel_id):
    return json.dumps({
        "inline": True,
        "buttons": [
            [{"action": {"type": "callback", "label": "⚔️ Сразиться", "payload": json.dumps({"cmd": "duel_accept", "duel_id": duel_id})}, "color": "positive"}]
        ]
    }, ensure_ascii=False)

# ===== ОСНОВНОЙ ЦИКЛ =====
init_db()

while True:
    try:
        for event in longpoll.listen():
            
            # --- КНОПКА ДУЭЛИ ---
            if event.type == VkBotEventType.MESSAGE_EVENT:
                payload = event.object.payload
                peer_id = event.object.peer_id
                user_id = event.object.user_id
                event_id = event.object.event_id
                cm_id = event.object.conversation_message_id
                
                if payload.get("cmd") == "duel_accept":
                    duel_id = payload.get("duel_id")
                    conn = get_db()
                    c = conn.cursor()
                    c.execute("SELECT challenger, bet, peer_id FROM active_duels WHERE msg_id = ?", (duel_id,))
                    row = c.fetchone()
                    
                    if row:
                        challenger, bet, duel_peer = row
                        if str(user_id) == challenger:
                            vk.messages.sendMessageEventAnswer(event_id=event_id, user_id=user_id, peer_id=peer_id, event_data=json.dumps({"type": "show_snackbar", "text": "❌ Нельзя драться с собой!"}))
                            conn.close(); continue
                        if get_balance(user_id) < bet:
                            vk.messages.sendMessageEventAnswer(event_id=event_id, user_id=user_id, peer_id=peer_id, event_data=json.dumps({"type": "show_snackbar", "text": "❌ Не хватает денег!"}))
                            conn.close(); continue
                            
                        winner_id = random.choice([int(challenger), user_id])
                        loser_id = int(challenger) if winner_id == user_id else user_id
                        prize = int(bet * 1.8)
                        
                        update_balance(winner_id, prize)
                        update_balance(loser_id, -bet)
                        
                        c.execute("DELETE FROM active_duels WHERE msg_id = ?", (duel_id,))
                        conn.commit()
                        
                        winner_name = get_user_name(winner_id)
                        loser_name = get_user_name(loser_id)
                        
                        msg_text = (
                            f"⚔️ Дуэль завершена!\n\n"
                            f"🏆 Победитель: {winner_name}\n"
                            f"❌ Проигравший: {loser_name}\n\n"
                            f"💰 Выигрыш: {prize}$"
                        )
                        vk.messages.edit(peer_id=peer_id, conversation_message_id=cm_id, message=msg_text)
                        vk.messages.sendMessageEventAnswer(event_id=event_id, user_id=user_id, peer_id=peer_id, event_data=json.dumps({"type": "show_snackbar", "text": "⚔️ Дуэль завершена!"}))
                    conn.close()
                continue

            # --- ТЕКСТОВЫЕ КОМАНДЫ ---
            if event.type == VkBotEventType.MESSAGE_NEW:
                msg = event.object.message
                user_id = msg['from_id']
                peer_id = msg['peer_id']
                text = msg.get('text', '').strip().lower()
                is_ls = (peer_id == user_id)
                
                balance = get_balance(user_id)
                clean_text = text.replace("/", "").strip()
                parts = clean_text.split()
                
                reply_to_id = msg.get('id')

                if not text: continue

                # 1. ПОМОЩЬ
                if clean_text in ["help", "помощь", "команды"]:
                    help_text = (
                        "📖 Доступные команды:\n\n"
                        "💼 Работа — Заработать деньги\n"
                        "🎰 /рулетка [цвет/чет] [ставка] — Игра\n"
                        "⚔️ /duel [сумма] — Дуэль\n"
                        "🎁 /бонус — Бонус (раз в 10 минут)\n"
                        "🎁 /promo [код] — Активировать промокод\n"
                        "📜 /промолист — Список активных промокодов\n"
                        "👤 /профиль — Твой баланс\n"
                        "🏆 /топ — Топ богачей"
                    )
                    send_msg(peer_id, help_text, get_main_kb() if is_ls else None, reply_to=reply_to_id)

                # 2. РАБОТА
                elif text == "💼 работа":
                    earned = random.randint(100, 500)
                    update_balance(user_id, earned)
                    send_msg(peer_id, f"✅ Ты заработал {earned}$!\n💰 Баланс: {get_balance(user_id)}$", get_main_kb(), reply_to=reply_to_id)
                
                # 3. ПРОФИЛЬ
                elif clean_text in ["профиль", "баланс"]:
                    send_msg(peer_id, f"👤 Твой профиль:\n💰 Баланс: {balance}$\n🆔 ID: {user_id}", get_main_kb() if is_ls else None, reply_to=reply_to_id)
                
                # 4. ТОП
                elif clean_text == "топ":
                    conn = get_db()
                    c = conn.cursor()
                    c.execute("SELECT user_id, balance FROM users WHERE balance > 2 ORDER BY balance DESC LIMIT 10")
                    rows = c.fetchall()
                    conn.close()
                    
                    top_text = "🏆 Топ 10 богачей:\n\n"
                    if not rows:
                        top_text += "Пока пусто."
                    else:
                        for i, r in enumerate(rows, 1):
                            u_name = get_user_name(r[0])
                            formatted_bal = f"{r[1]:,}".replace(",", ".")
                            top_text += f"{i}. {u_name} — {formatted_bal}$\n"
                    send_msg(peer_id, top_text, get_main_kb() if is_ls else None, reply_to=reply_to_id)
                
                # 5. РУЛЕТКА
                elif clean_text.startswith("рулетка") or clean_text.startswith("рул"):
                    if len(parts) >= 3:
                        choice = parts[1]
                        bet_str = parts[-1]
                        
                        if bet_str in ["вб", "всё", "все"]: bet = balance
                        elif bet_str.isdigit(): bet = int(bet_str)
                        else:
                            send_msg(peer_id, "❌ Неверная ставка.", reply_to=reply_to_id); continue

                        if bet < 10 or bet > balance:
                            send_msg(peer_id, f"❌ Мин. ставка 10, у тебя {balance}$", reply_to=reply_to_id); continue

                        res = random.randint(0, 36)
                        red_numbers = [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]
                        
                        if res in red_numbers:
                            color_name = "Красное"; color_emoji = "🔴"
                        elif res == 0:
                            color_name = "Зеро"; color_emoji = "🟢"
                        else:
                            color_name = "Черное"; color_emoji = "⚫"

                        if res == 0: even_name = "Ноль"
                        elif res % 2 == 0: even_name = "Четное"
                        else: even_name = "Нечетное"

                        win = False
                        if choice.isdigit() and int(choice) == res: win = True
                        elif choice in ["красное", "красный", "кр"] and res in red_numbers: win = True
                        elif choice in ["черное", "черный", "чр"] and res not in red_numbers and res != 0: win = True
                        elif choice in ["чет", "четное"] and res % 2 == 0 and res != 0: win = True
                        elif choice in ["нечет", "нечетное"] and res % 2 != 0: win = True

                        if win:
                            update_balance(user_id, bet)
                            msg_text = (
                                f"🎰 Выпало: {res} {color_emoji} ({color_name}, {even_name})\n\n"
                                f"✅ Ты выиграл: +{bet}$\n💰 Баланс: {get_balance(user_id)}$"
                            )
                        else:
                            update_balance(user_id, -bet)
                            msg_text = (
                                f"🎰 Выпало: {res} {color_emoji} ({color_name}, {even_name})\n\n"
                                f"😔 Ты проиграл: -{bet}$\n💰 Баланс: {get_balance(user_id)}$"
                            )
                        send_msg(peer_id, msg_text, get_main_kb() if is_ls else None, reply_to=reply_to_id)
                    else:
                        send_msg(peer_id, "❌ Формат: /рулетка красное 500", reply_to=reply_to_id)
                
                # 6. ДУЭЛИ
                elif clean_text.startswith("duel"):
                    if len(parts) == 2 and parts[1].isdigit():
                        bet = int(parts[1])
                        if bet < 50 or bet > 2000:
                            send_msg(peer_id, "❌ Ставка от 50 до 2000.", reply_to=reply_to_id)
                            continue
                        if balance < bet:
                            send_msg(peer_id, "❌ Не хватает монет.", reply_to=reply_to_id)
                            continue
                            
                        duel_id = str(random.randint(10000, 99999))
                        conn = get_db()
                        c = conn.cursor()
                        c.execute("REPLACE INTO active_duels (msg_id, challenger, bet, peer_id) VALUES (?, ?, ?, ?)", (duel_id, str(user_id), bet, str(peer_id)))
                        conn.commit()
                        conn.close()
                        
                        duel_text = (
                            f"⚔️ Дуэль!\n"
                            f"👤 Создатель: {get_user_name(user_id)}\n"
                            f"💰 Ставка: {bet}$\n\n"
                            f"🌑 Приз: {int(bet*1.8)}$\n"
                            f"⚡ Нажми кнопку ниже!"
                        )
                        send_msg(peer_id, duel_text, get_duel_kb(duel_id), reply_to=reply_to_id)
                    else:
                        send_msg(peer_id, "❌ Формат: /duel [сумма] (от 50 до 2000)", reply_to=reply_to_id)

                # 7. БОНУС
                elif clean_text == "бонус":
                    uid = str(user_id)
                    current_time = int(time.time())
                    conn = get_db()
                    c = conn.cursor()
                    c.execute("SELECT last_used FROM bonus_cd WHERE user_id = ?", (uid,))
                    row = c.fetchone()
                    last_use = row[0] if row else 0
                    
                    if current_time - last_use < BONUS_CD:
                        remaining = BONUS_CD - (current_time - last_use)
                        send_msg(peer_id, f"⏳ Бонус доступен через {remaining // 60} мин. {remaining % 60} сек.", reply_to=reply_to_id)
                        conn.close(); continue
                        
                    bonus_amount = random.choice([100000, 200000, 500000])
                    update_balance(user_id, bonus_amount)
                    c.execute("REPLACE INTO bonus_cd (user_id, last_used) VALUES (?, ?)", (uid, current_time))
                    conn.commit()
                    conn.close()
                    
                    msg_text = f"🎁 Бонус получен! ✨\n+{bonus_amount:,}$\n💰 Баланс: {get_balance(user_id):,}$".replace(",", ".")
                    send_msg(peer_id, msg_text, get_main_kb() if is_ls else None, reply_to=reply_to_id)

                # 8. ВЫДАЧА ДЕНЕГ (ТОЛЬКО ВЛАДЕЛЕЦ)
                elif clean_text.startswith("деньги") and user_id == ADMIN_ID:
                    if len(parts) == 2 and parts[1].isdigit() and msg.get('reply_message'):
                        amount = int(parts[1])
                        target_id = msg['reply_message']['from_id']
                        update_balance(target_id, amount)
                        
                        target_name = get_user_name(target_id)
                        send_msg(peer_id, f"💰 Владелец выдал {amount}$ игроку {target_name}!", reply_to=reply_to_id)
                    else:
                        send_msg(peer_id, "❌ Формат: /деньги [сумма] (ответом на сообщение)", reply_to=reply_to_id)

                # 9. СОЗДАНИЕ ПРОМОКОДА (ТОЛЬКО ВЛАДЕЛЕЦ)
                elif clean_text.startswith("создать") and user_id == ADMIN_ID:
                    if len(parts) == 4 and parts[2].isdigit() and parts[3].isdigit():
                        code = parts[1]
                        amount = int(parts[2])
                        limit = int(parts[3])
                        
                        conn = get_db()
                        c = conn.cursor()
                        c.execute("REPLACE INTO promos (code, amount, limit_count, used_by) VALUES (?, ?, ?, '')", (code, amount, limit))
                        conn.commit()
                        conn.close()
                        send_msg(peer_id, f"✅ Промокод `{code}` на {amount}$ (Лимит: {limit}) создан!", reply_to=reply_to_id)
                    else:
                        send_msg(peer_id, "❌ Формат: /создать [код] [сумма] [лимит]", reply_to=reply_to_id)

                # 10. СПИСОК ПРОМОКОДОВ
                elif clean_text == "промолист":
                    conn = get_db()
                    c = conn.cursor()
                    c.execute("SELECT code, amount, limit_count, used_by FROM promos")
                    rows = c.fetchall()
                    conn.close()
                    if not rows:
                        send_msg(peer_id, "❌ Активных промокодов нет.", reply_to=reply_to_id)
                    else:
                        promo_list = "🎁 Активные промокоды:\n\n"
                        for r in rows:
                            used_count = len(r[3].split(",")) if r[3] else 0
                            promo_list += f"▪️ `{r[0]}` — {r[1]}$ (Активировали: {used_count}/{r[2]})\n"
                        send_msg(peer_id, promo_list, reply_to=reply_to_id)

                # 11. АКТИВАЦИЯ ПРОМОКОДА
                elif clean_text.startswith("promo"):
                    if len(parts) == 2:
                        code = parts[1]
                        conn = get_db()
                        c = conn.cursor()
                        c.execute("SELECT amount, limit_count, used_by FROM promos WHERE code = ?", (code,))
                        row = c.fetchone()
                        
                        if not row:
                            send_msg(peer_id, "❌ Промокод не существует или уже исчерпан.", reply_to=reply_to_id)
                            conn.close(); continue
                            
                        amount, limit, used_by_str = row
                        used_by = used_by_str.split(",") if used_by_str else []
                        
                        if len(used_by) >= limit:
                            c.execute("DELETE FROM promos WHERE code = ?", (code,))
                            conn.commit()
                            send_msg(peer_id, "❌ Промокод больше не действителен.", reply_to=reply_to_id)
                            conn.close(); continue
                            
                        if str(user_id) in used_by:
                            send_msg(peer_id, "❌ Ты уже активировал этот промокод!", reply_to=reply_to_id)
                            conn.close(); continue
                            
                        used_by.append(str(user_id))
                        update_balance(user_id, amount)
                        
                        if len(used_by) >= limit:
                            c.execute("DELETE FROM promos WHERE code = ?", (code,))
                            msg_text = f"✅ Промокод активирован! +{amount}$\n⚠️ Это была последняя активация. Промокод удален."
                        else:
                            c.execute("UPDATE promos SET used_by = ? WHERE code = ?", (",".join(used_by), code))
                            msg_text = f"✅ Промокод активирован! +{amount}$\nОсталось активаций: {limit - len(used_by)}"
                            
                        conn.commit()
                        conn.close()
                        send_msg(peer_id, msg_text, reply_to=reply_to_id)
                    else:
                        send_msg(peer_id, "❌ Формат: /promo [код]", reply_to=reply_to_id)

    except Exception as e:
        print(f"⚠️ Ошибка в цикле: {e}")
        time.sleep(1)
