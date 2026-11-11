import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
import json, random, time, os
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

print("--- БОТ ЗАПУЩЕН УСПЕШНО ---")

# ===== БАЗА ДАННЫХ =====
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, balance INTEGER DEFAULT 1000)")
    c.execute("CREATE TABLE IF NOT EXISTS promos (code TEXT PRIMARY KEY, amount INTEGER, limit_count INTEGER, used_by TEXT DEFAULT '')")
    c.execute("CREATE TABLE IF NOT EXISTS fortune_cd (user_id TEXT PRIMARY KEY, last_used INTEGER)")
    c.execute("CREATE TABLE IF NOT EXISTS bonus_cd (user_id TEXT PRIMARY KEY, last_used INTEGER)")
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

def get_user_name(user_id):
    try:
        user_info = vk.users.get(user_ids=user_id)[0]
        return f"[id{user_id}|{user_info['first_name']} {user_info['last_name']}]"
    except:
        return f"[id{user_id}|Игрок]"

def send_msg(peer_id, message, keyboard=None, reply_to=None):
    try:
        params = {'peer_id': peer_id, 'message': message, 'random_id': random.randint(1, 2**31 - 1)}
        if keyboard: params['keyboard'] = keyboard
        if reply_to: params['reply_to'] = reply_to
        params['disable_mentions'] = 1 
        return vk.messages.send(**params)
    except Exception as e:
        print(f"Ошибка отправки: {e}")

# ===== КЛАВИАТУРЫ =====
def get_main_kb():
    return json.dumps({"one_time": False, "buttons": [
        [{"action": {"type": "text", "label": "💼 Работа"}, "color": "positive"}, {"action": {"type": "text", "label": "🎰 Рулетка"}, "color": "primary"}],
        [{"action": {"type": "text", "label": "👤 Профиль"}, "color": "secondary"}, {"action": {"type": "text", "label": "🏆 Топ"}, "color": "secondary"}]]}, ensure_ascii=False)

# ===== ОСНОВНОЙ ЦИКЛ =====
init_db()

while True:
    try:
        for event in longpoll.listen():
            if event.type == VkBotEventType.MESSAGE_NEW:
                msg = event.object.message
                user_id = msg['from_id']
                peer_id = msg['peer_id']
                text = msg.get('text', '').strip().lower()
                is_ls = (peer_id == user_id)
                
                balance = get_balance(user_id)
                clean_text = text.replace("/", "").strip()
                parts = clean_text.split()
                
                reply_to_id = msg.get('id') if not is_ls else None

                if not text and is_ls:
                    send_msg(peer_id, f"👋 Привет! Твой баланс: {balance}$\nЖми «Работа» или пиши /help", get_main_kb())
                    continue
                if not text: continue

                # 1. ПОМОЩЬ
                if clean_text in ["help", "помощь", "команды"]:
                    help_text = (
                        "📖 **Игровые команды:**\n\n"
                        "🎰 /рулетка [цвет/чет] [ставка]\n"
                        "🎲 /фортуна - Крутить (100$)\n"
                        "🎁 /бонус - Получить бонус (раз в 10 мин)\n"
                        "✂️ /rps [фигура] [ставка]\n"
                        "⚔️ /duel [сумма] - Вызов (реплай)\n"
                        "👤 /профиль - Твой баланс\n"
                        "🏆 /топ - Богачи\n"
                        "🎁 /promo [код] - Активировать"
                    )
                    send_msg(peer_id, help_text, keyboard=get_main_kb() if is_ls else None, reply_to=reply_to_id)
                
                # 2. РАБОТА
                elif text == "💼 работа":
                    earned = random.randint(200, 800)
                    update_balance(user_id, earned)
                    send_msg(peer_id, f"✅ Ты заработал {earned}$!\n💰 Баланс: {get_balance(user_id)}$", get_main_kb())
                
                # 3. ПРОФИЛЬ
                elif clean_text in ["профиль", "баланс"]:
                    send_msg(peer_id, f"👤 Твой профиль:\n💰 Баланс: {balance}$\n🆔 ID: {user_id}", keyboard=get_main_kb() if is_ls else None, reply_to=reply_to_id)
                
                # 4. ТОП
                elif clean_text == "топ":
                    conn = sqlite3.connect(DB_FILE)
                    c = conn.cursor()
                    c.execute("SELECT user_id, balance FROM users WHERE balance > 2 ORDER BY balance DESC LIMIT 10")
                    rows = c.fetchall()
                    conn.close()
                    top_text = "🏆 Топ 10 по монетам:\n\n"
                    if not rows:
                        top_text += "Пока никого нет."
                    else:
                        for i, r in enumerate(rows, 1):
                            u_id = r[0]
                            u_bal = r[1]
                            u_name = get_user_name(u_id)
                            formatted_bal = f"{u_bal:,}".replace(",", ".")
                            top_text += f"{i}. {u_name} — {formatted_bal}\n"
                    send_msg(peer_id, top_text, keyboard=get_main_kb() if is_ls else None, reply_to=reply_to_id)
                
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
                            color_name = "красное"; color_emoji = "🔴"
                        elif res == 0:
                            color_name = "зеленое"; color_emoji = "🟢"
                        else:
                            color_name = "чёрное"; color_emoji = "⚫"

                        if res == 0: even_name = "ноль"
                        elif res % 2 == 0: even_name = "чётное"
                        else: even_name = "нечётное"

                        win = False
                        if choice.isdigit() and int(choice) == res: win = True
                        elif choice in ["красное", "красный", "кр"] and res in red_numbers: win = True
                        elif choice in ["черное", "черный", "чр"] and res not in red_numbers and res != 0: win = True
                        elif choice in ["чет", "четное"] and res % 2 == 0 and res != 0: win = True
                        elif choice in ["нечет", "нечетное"] and res % 2 != 0: win = True

                        if win:
                            update_balance(user_id, bet)
                            msg_text = (
                                f"🎰 Выпало: {res} {color_emoji} ({color_name}, {even_name})\n"
                                f"{get_user_name(user_id)} — ставка {bet}$ на {choice}\n\n"
                                f"✅ Выигрыш x2: +{bet}$\n💰 Баланс: {get_balance(user_id)}$"
                            )
                        else:
                            update_balance(user_id, -bet)
                            msg_text = (
                                f"🎰 Выпало: {res} {color_emoji} ({color_name}, {even_name})\n"
                                f"{get_user_name(user_id)} — ставка {bet}$ на {choice}\n\n"
                                f"😔 Проигрыш: -{bet}$\n💰 Баланс: {get_balance(user_id)}$"
                            )
                        send_msg(peer_id, msg_text, keyboard=get_main_kb() if is_ls else None, reply_to=reply_to_id)
                    else:
                        send_msg(peer_id, "❌ Формат: /рулетка красное 500", reply_to=reply_to_id)
                
                # 6. ФОРТУНА
                elif clean_text.startswith("фортуна"):
                    uid = str(user_id)
                    current_time = int(time.time())
                    conn = sqlite3.connect(DB_FILE)
                    c = conn.cursor()
                    c.execute("SELECT last_used FROM fortune_cd WHERE user_id = ?", (uid,))
                    row = c.fetchone()
                    last_use = row[0] if row else 0
                    
                    if current_time - last_use < FORTUNA_CD:
                        remaining = FORTUNA_CD - (current_time - last_use)
                        send_msg(peer_id, f"⏳ Фортуна доступна через {remaining // 60} мин. {remaining % 60} сек.", reply_to=reply_to_id)
                        conn.close(); continue
                        
                    if balance < 100: 
                        send_msg(peer_id, "❌ Фортуна стоит 100$.", reply_to=reply_to_id)
                        conn.close(); continue
                    
                    update_balance(user_id, -100)
                    c.execute("REPLACE INTO fortune_cd (user_id, last_used) VALUES (?, ?)", (uid, current_time))
                    conn.commit()
                    conn.close()
                    
                    prize = random.choice([0, 50, 100, 200, 500, 1000, 5000])
                    update_balance(user_id, prize)
                    send_msg(peer_id, f"🎰 Выпало: {prize}$!\n💰 Баланс: {get_balance(user_id)}$", reply_to=reply_to_id)

                # 7. БОНУС
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
                        send_msg(peer_id, f"⏳ Бонус доступен через {remaining // 60} мин. {remaining % 60} сек.", reply_to=reply_to_id)
                        conn.close(); continue
                        
                    bonus_amount = random.choice([1000000, 1500000, 2000000])
                    update_balance(user_id, bonus_amount)
                    c.execute("REPLACE INTO bonus_cd (user_id, last_used) VALUES (?, ?)", (uid, current_time))
                    conn.commit()
                    conn.close()
                    
                    msg_text = (
                        f"🎁 Бонус получен! ✨ VIP\n"
                        f"+{bonus_amount:,}\n".replace(",", ".") +
                        f"💰 Баланс: {get_balance(user_id):,}\n".replace(",", ".")
                    )
                    send_msg(peer_id, msg_text, reply_to=reply_to_id)

                # 8. RPS (Камень-Ножницы-Бумага)
                elif clean_text.startswith("rps"):
                    if len(parts) == 3 and parts[2].isdigit():
                        bet = int(parts[2])
                        p_choice = parts[1]
                        if bet > balance or bet < 10:
                            send_msg(peer_id, f"❌ Мин. ставка 10, у тебя {balance}$", reply_to=reply_to_id)
                        elif p_choice not in ["камень", "ножницы", "бумага"]:
                            send_msg(peer_id, "❌ Выбери: камень, ножницы или бумага.", reply_to=reply_to_id)
                        else:
                            b_choice = random.choice(["камень", "ножницы", "бумага"])
                            if p_choice == b_choice:
                                res = f"🤝 Ничья! Бот выбрал {b_choice}."
                            elif (p_choice == "камень" and b_choice == "ножницы") or (p_choice == "ножницы" and b_choice == "бумага") or (p_choice == "бумага" and b_choice == "камень"):
                                update_balance(user_id, bet)
                                res = f"🎉 Ты победил! Бот выбрал {b_choice}. +{bet}$"
                            else:
                                update_balance(user_id, -bet)
                                res = f"😔 Ты проиграл. Бот выбрал {b_choice}. -{bet}$"
                            send_msg(peer_id, res + f"\nБаланс: {get_balance(user_id)}$", reply_to=reply_to_id)
                    else:
                        send_msg(peer_id, "❌ Формат: /rps камень 500", reply_to=reply_to_id)

                # 9. ДУЭЛИ
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
                        conn = sqlite3.connect(DB_FILE)
                        c = conn.cursor()
                        c.execute("REPLACE INTO active_duels (msg_id, challenger, bet, peer_id) VALUES (?, ?, ?, ?)", (duel_id, str(user_id), bet, str(peer_id)))
                        conn.commit()
                        conn.close()
                        
                        duel_text = (
                            f"⚔️ Дуэль на монеты!\n"
                            f"👤 Создатель: {get_user_name(user_id)}\n"
                            f"💰 Ставка: {bet}\n\n"
                            f"🌑 Приз: {int(bet*1.8)} победителю\n"
                            f"⚡ Напиши /принять, чтобы сразиться!"
                        )
                        send_msg(peer_id, duel_text, reply_to=reply_to_id)
                    else:
                        send_msg(peer_id, "❌ Формат: /duel [сумма] (от 50 до 2000)", reply_to=reply_to_id)
                
                # 10. ПРИНЯТЬ ДУЭЛЬ
                elif clean_text == "принять":
                    conn = sqlite3.connect(DB_FILE)
                    c = conn.cursor()
                    c.execute("SELECT challenger, bet, peer_id FROM active_duels WHERE peer_id = ?", (str(peer_id),))
                    row = c.fetchone()
                    if row:
                        challenger, bet, duel_peer = row
                        if get_balance(user_id) < bet:
                            send_msg(peer_id, "❌ У тебя не хватает денег на дуэль.", reply_to=reply_to_id)
                        else:
                            winner_id = random.choice([int(challenger), user_id])
                            loser_id = int(challenger) if winner_id == user_id else user_id
                            prize = int(bet * 1.8)
                            update_balance(winner_id, prize)
                            update_balance(loser_id, -bet)
                            c.execute("DELETE FROM active_duels WHERE peer_id = ?", (str(peer_id),))
                            conn.commit()
                            send_msg(peer_id, f"⚔️ Дуэль окончена! Победил {get_user_name(winner_id)} и забрал {prize}$!", reply_to=reply_to_id)
                    else:
                        send_msg(peer_id, "❌ Нет активных дуэлей.", reply_to=reply_to_id)
                    conn.close()

                # 11. СОЗДАНИЕ ПРОМОКОДА
                elif (clean_text.startswith("создать") or clean_text.startswith("промокод")) and user_id == ADMIN_ID:
                    if len(parts) == 3:
                        _, code, amount = parts
                        limit = 50
                    elif len(parts) == 4:
                        _, code, amount, limit = parts
                        limit = int(limit)
                    else:
                        send_msg(peer_id, "❌ Формат: /промокод код сумма [лимит]", reply_to=reply_to_id)
                        continue
                        
                    conn = sqlite3.connect(DB_FILE)
                    c = conn.cursor()
                    c.execute("REPLACE INTO promos (code, amount, limit_count, used_by) VALUES (?, ?, ?, '')", (code, int(amount), limit))
                    conn.commit()
                    conn.close()
                    send_msg(peer_id, f"✅ Промокод `{code}` на {amount}$ (Лимит: {limit}) создан!", reply_to=reply_to_id)

                # 12. АКТИВАЦИЯ ПРОМОКОДА
                elif clean_text.startswith("promo"):
                    try:
                        code = parts[1]
                        conn = sqlite3.connect(DB_FILE)
                        c = conn.cursor()
                        c.execute("SELECT amount, limit_count, used_by FROM promos WHERE code = ?", (code,))
                        row = c.fetchone()
                        if not row: 
                            send_msg(peer_id, "❌ Промокод не существует или истекло промо.", reply_to=reply_to_id)
                            conn.close()
                            continue
                            
                        amount, limit, used_by_str = row
                        used_by = used_by_str.split(",") if used_by_str else []
                        
                        if len(used_by) >= limit:
                            c.execute("DELETE FROM promos WHERE code = ?", (code,))
                            conn.commit()
                            send_msg(peer_id, "❌ Истекло промо. Лимит активаций закончился.", reply_to=reply_to_id)
                            conn.close()
                            continue
                            
                        if str(user_id) in used_by:
                            send_msg(peer_id, "❌ Ты уже активировал этот промокод!", reply_to=reply_to_id)
                            conn.close()
                            continue
                        
                        used_by.append(str(user_id))
                        c.execute("UPDATE promos SET used_by = ? WHERE code = ?", (",".join(used_by), code))
                        conn.commit()
                        update_balance(user_id, amount)
                        send_msg(peer_id, f"✅ Промокод активирован! +{amount}$\nОсталось активаций: {limit - len(used_by)}", reply_to=reply_to_id)
                        conn.close()
                    except:
                        send_msg(peer_id, "❌ Формат: /promo код", reply_to=reply_to_id)

    except Exception as e:
        print(f"⚠️ Ошибка в цикле: {e}")
        time.sleep(1)
