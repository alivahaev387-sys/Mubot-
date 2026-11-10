import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
import json, random, time, asyncio
import aiosqlite

# ===== НАСТРОЙКИ =====
TOKEN = "vk1.a.n-y1VnQMFI87cAGH7zXHwYy6LncLM_UuAaCihe6dlWxUBLGwS8no-KjRmFrA9zmwy-STfP7f2VZOHArq1-WVKYVRUA3H1F3-pO5gtXRxEziw3u3st-dTYHNiK_an2ZcbUIpXYNy98HHTGQv12wFtMLsSASQ0kO0ke0B0DRsXc7hn-LQrYcpbu54a_kQmP7dxBO5a8gTmuS9Dn9LH7oMLfE6G6_GPJZxJAgkwzptCnWw"
GROUP_ID = 243089386
ADMIN_ID = 200005093141 
FORTUNA_CD = 600

vk_session = vk_api.VkApi(token=TOKEN)
longpoll = VkBotLongPoll(vk_session, GROUP_ID)
vk = vk_session.get_api()

# ===== БАЗА ДАННЫХ (Асинхронный SQLite) =====
DB_NAME = "game.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, balance INTEGER DEFAULT 1000)")
        await db.execute("CREATE TABLE IF NOT EXISTS promos (code TEXT PRIMARY KEY, amount INTEGER, limit_count INTEGER, used_by TEXT DEFAULT '')")
        await db.execute("CREATE TABLE IF NOT EXISTS fortune_cd (user_id TEXT PRIMARY KEY, last_used INTEGER)")
        await db.execute("CREATE TABLE IF NOT EXISTS games (game_id TEXT PRIMARY KEY, user_id TEXT, bet INTEGER, mines TEXT, opened TEXT, multiplier REAL)")
        await db.commit()

async def get_balance(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT balance FROM users WHERE user_id = ?", (str(user_id),)) as cursor:
            row = await cursor.fetchone()
            if not row:
                await db.execute("INSERT INTO users (user_id, balance) VALUES (?, 1000)", (str(user_id),))
                await db.commit()
                return 1000
            return row[0]

async def update_balance(user_id, amount):
    bal = await get_balance(user_id)
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET balance = ? WHERE user_id = ?", (bal + amount, str(user_id)))
        await db.commit()

def send_msg(peer_id, message, keyboard=None, reply_to=None):
    try:
        params = {'peer_id': peer_id, 'message': message, 'random_id': random.randint(1, 2**31 - 1)}
        if keyboard: params['keyboard'] = keyboard
        if reply_to: params['reply_to'] = reply_to
        return vk.messages.send(**params)
    except Exception as e:
        print(f"Ошибка отправки: {e}")

def edit_msg(peer_id, cm_id, message, keyboard=None):
    try:
        params = {'peer_id': peer_id, 'message': message, 'conversation_message_id': cm_id}
        if keyboard: params['keyboard'] = keyboard
        vk.messages.edit(**params)
    except Exception as e:
        print(f"Ошибка редактирования: {e}")

# ===== КЛАВИАТУРЫ =====
def get_work_kb():
    return json.dumps({"one_time": False, "buttons": [
        [{"action": {"type": "text", "label": "🚕 Такси"}, "color": "primary"}, {"action": {"type": "text", "label": "🎣 Рыбалка"}, "color": "primary"}],
        [{"action": {"type": "text", "label": "🏹 Охота"}, "color": "primary"}, {"action": {"type": "text", "label": "🔙 Назад"}, "color": "secondary"}]]}, ensure_ascii=False)

def get_main_kb():
    return json.dumps({"one_time": False, "buttons": [
        [{"action": {"type": "text", "label": "💼 Работа"}, "color": "positive"}],
        [{"action": {"type": "text", "label": "📖 Помощь"}, "color": "secondary"}]]}, ensure_ascii=False)

def get_sub_kb():
    return json.dumps({"inline": True, "buttons": [
        [{"action": {"type": "open_link", "link": f"https://vk.com/public{GROUP_ID}", "label": "📢 Подписаться"}}]]}, ensure_ascii=False)

def get_mines_count_kb(game_id):
    kb = {"inline": True, "buttons": []}
    row = []
    for i in range(2, 9):
        row.append({"action": {"type": "callback", "label": f"{i} 💣", "payload": json.dumps({"cmd": "mines_set", "game_id": game_id, "count": i})}, "color": "secondary"})
        if len(row) == 3:
            kb["buttons"].append(row); row = []
    if row: kb["buttons"].append(row)
    return json.dumps(kb, ensure_ascii=False)

def get_mines_field_kb(game):
    kb = {"inline": True, "buttons": []}
    row = []
    for i in range(1, 10):
        if i in game["opened"]:
            row.append({"action": {"type": "callback", "label": "💎" if i not in game["mines"] else "💥", "payload": "{}"}, "color": "positive" if i not in game["mines"] else "negative"})
        else:
            row.append({"action": {"type": "callback", "label": str(i), "payload": json.dumps({"cmd": "mines_click", "game_id": game["id"], "cell": i})}, "color": "secondary"})
        if len(row) == 3:
            kb["buttons"].append(row); row = []
    kb["buttons"].append([{"action": {"type": "callback", "label": "💰 Забрать", "payload": json.dumps({"cmd": "mines_cashout", "game_id": game["id"]})}, "color": "positive"}])
    return json.dumps(kb, ensure_ascii=False)

# ===== ЛОГИКА =====
async def process_roulette(user_id, peer_id, choice, bet_str, reply_to=None, is_ls=False):
    balance = await get_balance(user_id)
    if bet_str in ["вб", "всё", "все"]: bet = balance
    elif bet_str.isdigit(): bet = int(bet_str)
    elif "к" in bet_str and bet_str.replace("к", "").isdigit(): bet = int(bet_str.replace("к", "")) * 1000
    else:
        send_msg(peer_id, "❌ Неверная ставка.", reply_to=reply_to); return

    if bet < 10 and bet != balance:
        send_msg(peer_id, "❌ Мин. ставка 10$", reply_to=reply_to); return
    if bet > balance:
        send_msg(peer_id, f"❌ У тебя нет столько денег! Баланс: {balance}$", reply_to=reply_to); return

    res = random.randint(0, 36)
    red_numbers = [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]
    win, win_multiplier = False, 2
    choice = choice.replace("/", "").strip()
    
    if choice.isdigit():
        if int(choice) == res: win = True; win_multiplier = 36
    elif choice in ["красное", "красный", "кр"]:
        if res in red_numbers: win = True
    elif choice in ["черное", "черный", "чр"]:
        if res not in red_numbers and res != 0: win = True
    elif choice in ["чет", "четное"]:
        if res % 2 == 0 and res != 0: win = True
    elif choice in ["нечет", "нечетное"]:
        if res % 2 != 0: win = True
    elif choice in ["1-12", "13-24", "25-36", "1-18", "19-36"]:
        win_multiplier = 3 if choice in ["1-12", "13-24", "25-36"] else 2
        if choice == "1-12" and 1 <= res <= 12: win = True
        elif choice == "13-24" and 13 <= res <= 24: win = True
        elif choice == "25-36" and 25 <= res <= 36: win = True
        elif choice == "1-18" and 1 <= res <= 18: win = True
        elif choice == "19-36" and 19 <= res <= 36: win = True
    else:
        send_msg(peer_id, "❌ Не понял ставку.", reply_to=reply_to); return

    color_emoji = "🔴" if res in red_numbers else "⚫" if res != 0 else "🟢"
    
    if win:
        win_amount = bet * win_multiplier
        await update_balance(user_id, win_amount)
        msg = f"🎉 ПОБЕДА! Выпало {res} {color_emoji}\nТы выиграл {win_amount}$\nБаланс: {await get_balance(user_id)}$"
    else:
        await update_balance(user_id, -bet)
        msg = f"😔 ПРОИГРЫШ. Выпало {res} {color_emoji}\nТы потерял {bet}$\nБаланс: {await get_balance(user_id)}$"
        
    kb = get_main_kb() if is_ls else None
    send_msg(peer_id, msg, keyboard=kb, reply_to=reply_to)

async def process_fortune(user_id, peer_id, reply_to=None, is_ls=False):
    uid = str(user_id)
    current_time = int(time.time())
    
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT last_used FROM fortune_cd WHERE user_id = ?", (uid,)) as cursor:
            row = await cursor.fetchone()
            last_use = row[0] if row else 0
            
    if current_time - last_use < FORTUNA_CD:
        remaining = FORTUNA_CD - (current_time - last_use)
        msg = f"⏳ Следующая фортуна доступна через {remaining // 60} мин. {remaining % 60} сек."
        send_msg(peer_id, msg, keyboard=get_main_kb() if is_ls else None, reply_to=reply_to); return

    balance = await get_balance(user_id)
    if balance < 100: 
        send_msg(peer_id, "❌ Фортуна стоит 100$. У тебя мало денег.", reply_to=reply_to); return
    
    await update_balance(user_id, -100)
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("REPLACE INTO fortune_cd (user_id, last_used) VALUES (?, ?)", (uid, current_time))
        await db.commit()
    
    prize = random.choice([0, 50, 100, 200, 500, 1000, 5000])
    await update_balance(user_id, prize)
    msg = f"🎰 Крутим фортуну...\nВыпало: {prize}$!\nБаланс: {await get_balance(user_id)}$"
    send_msg(peer_id, msg, keyboard=get_main_kb() if is_ls else None, reply_to=reply_to)

# ===== ОСНОВНОЙ ЦИКЛ =====
async def main():
    await init_db()
    print("БОТ ЗАПУЩЕН! МИНЫ С ИНТЕРФЕЙСОМ (PostgreSQL-ready архитектура).")

    for event in longpoll.listen():
        try:
            # ОБРАБОТКА КНОПОК
            if event.type == VkBotEventType.MESSAGE_EVENT:
                payload = event.object.payload
                peer_id, user_id, event_id, cm_id = event.object.peer_id, event.object.user_id, event.object.event_id, event.object.conversation_message_id
                
                if payload.get("cmd") == "mines_set":
                    game_id, mine_count = payload["game_id"], payload["count"]
                    async with aiosqlite.connect(DB_NAME) as db:
                        async with db.execute("SELECT bet FROM games WHERE game_id = ? AND user_id = ?", (game_id, str(user_id))) as cursor:
                            row = await cursor.fetchone()
                            if row:
                                bet = row[0]
                                mines = json.dumps(random.sample(range(1, 10), mine_count))
                                await db.execute("UPDATE games SET mines = ?, opened = '[]', multiplier = 1.0 WHERE game_id = ?", (mines, game_id))
                                await db.commit()
                                
                                game = {"id": game_id, "opened": [], "mines": json.loads(mines)}
                                msg_text = f"💣 Мины\nСтавка: {bet}$ | Мин: {mine_count} из 9\n\nВыбери клетку, чтобы открыть алмаз 💎"
                                edit_msg(peer_id, cm_id, msg_text, get_mines_field_kb(game))
                                vk.messages.sendMessageEventAnswer(event_id=event_id, user_id=user_id, peer_id=peer_id, event_data=json.dumps({"type": "show_snackbar", "text": "Игра началась!"}))
                
                elif payload.get("cmd") == "mines_click":
                    game_id, cell = payload["game_id"], payload["cell"]
                    async with aiosqlite.connect(DB_NAME) as db:
                        async with db.execute("SELECT bet, mines, opened, multiplier FROM games WHERE game_id = ? AND user_id = ?", (game_id, str(user_id))) as cursor:
                            row = await cursor.fetchone()
                            if row:
                                bet, mines_str, opened_str, mult = row
                                mines = json.loads(mines_str)
                                opened = json.loads(opened_str)
                                
                                if cell in opened: continue
                                opened.append(cell)
                                
                                if cell in mines:
                                    await update_balance(user_id, -bet)
                                    await db.execute("DELETE FROM games WHERE game_id = ?", (game_id,))
                                    await db.commit()
                                    game = {"id": game_id, "opened": list(range(1, 10)), "mines": mines}
                                    msg_text = f"💥 Вы попали на мину!\n\nПроигрыш: -{bet}$\nБаланс: {await get_balance(user_id)}$"
                                    edit_msg(peer_id, cm_id, msg_text, get_mines_field_kb(game))
                                    vk.messages.sendMessageEventAnswer(event_id=event_id, user_id=user_id, peer_id=peer_id, event_data=json.dumps({"type": "show_snackbar", "text": "💥 БУМ! Вы проиграли."}))
                                    continue
                                
                                opened_count, mines_count = len(opened), len(mines)
                                new_mult = 1.0
                                for i in range(opened_count):
                                    new_mult *= (9 - i) / (9 - mines_count - i)
                                new_mult = round(new_mult * 0.95, 2)
                                
                                await db.execute("UPDATE games SET opened = ?, multiplier = ? WHERE game_id = ?", (json.dumps(opened), new_mult, game_id))
                                await db.commit()
                                
                                win_amount = int(bet * new_mult)
                                game = {"id": game_id, "opened": opened, "mines": mines}
                                msg_text = (f"💣 Мины\nСтавка: {bet}$ | Мин: {mines_count} из 9\n\n"
                                            f"Открыто алмазов: {opened_count} | Коэф: x{new_mult}\n"
                                            f"Выигрыш сейчас: {win_amount}$\nСледующий алмаз даст больше!")
                                edit_msg(peer_id, cm_id, msg_text, get_mines_field_kb(game))
                                vk.messages.sendMessageEventAnswer(event_id=event_id, user_id=user_id, peer_id=peer_id, event_data=json.dumps({"type": "show_snackbar", "text": f"💎 Алмаз! x{new_mult}"}))
                
                elif payload.get("cmd") == "mines_cashout":
                    game_id = payload["game_id"]
                    async with aiosqlite.connect(DB_NAME) as db:
                        async with db.execute("SELECT bet, multiplier FROM games WHERE game_id = ? AND user_id = ?", (game_id, str(user_id))) as cursor:
                            row = await cursor.fetchone()
                            if row:
                                bet, mult = row
                                win_amount = int(bet * mult)
                                await update_balance(user_id, win_amount)
                                await db.execute("DELETE FROM games WHERE game_id = ?", (game_id,))
                                await db.commit()
                                msg_text = f"💰 Вы забрали выигрыш: {win_amount}$!\nБаланс: {await get_balance(user_id)}$"
                                edit_msg(peer_id, cm_id, msg_text, None)
                                vk.messages.sendMessageEventAnswer(event_id=event_id, user_id=user_id, peer_id=peer_id, event_data=json.dumps({"type": "show_snackbar", "text": "💰 Деньги у вас!"}))
                continue

            # ТЕКСТОВЫЕ СООБЩЕНИЯ
            if event.type == VkBotEventType.MESSAGE_NEW:
                msg = event.object.message
                user_id, peer_id = msg['from_id'], msg['peer_id']
                text = msg.get('text', '').strip()
                text_lower = text.lower()
                is_ls = (peer_id == user_id)
                balance = await get_balance(user_id)
                parts = text_lower.replace("/", "").split()

                if not text and is_ls:
                    send_msg(peer_id, f"👋 Привет! Твой баланс: {balance}$\nЖми «Работа» или пиши /help", get_main_kb()); continue
                if not text: continue

                if text_lower in ["/help", "help", "помощь"]:
                    help_text = "📖 Команды:\n/рулетка [цвет] [ставка]\n/фортуна\n/мины [ставка]\n/rps [фигура] [ставка]\n/duel [сумма] (реплай)\n/профиль\n/топ\n/promo [код]"
                    send_msg(peer_id, help_text, keyboard=get_main_kb() if is_ls else None, reply_to=msg.get('id')); continue

                if is_ls:
                    if text_lower in ["начать", "start", "меню", "привет"]:
                        send_msg(peer_id, f"🎰 Твой баланс: {balance}$\nЖми кнопку или пиши /help", get_main_kb())
                    elif text == "💼 Работа": send_msg(peer_id, "Выбери работу:", get_work_kb())
                    elif text == "🔙 Назад": send_msg(peer_id, "Меню:", get_main_kb())
                    elif text in ["🚕 Такси", "🎣 Рыбалка", "🏹 Охота"]:
                        earned = random.randint(200, 800); await update_balance(user_id, earned)
                        send_msg(peer_id, f"✅ Ты заработал {earned}$!\n💰 Баланс: {await get_balance(user_id)}$", get_work_kb())

                elif text_lower.startswith(("/мины", "мины")):
                    if len(parts) >= 2:
                        bet_str = parts[1]
                        bet = balance if bet_str in ["все", "вб", "всё"] else int(bet_str) if bet_str.isdigit() else int(bet_str[:-1]) * 1000 if bet_str.endswith("к") and bet_str[:-1].isdigit() else 0
                        if bet < 10 or bet > balance: send_msg(peer_id, f"❌ Мин. ставка 10, у тебя {balance}$", reply_to=msg.get('id')); continue
                        
                        game_id = str(random.randint(10000, 99999))
                        async with aiosqlite.connect(DB_NAME) as db:
                            await db.execute("INSERT INTO games (game_id, user_id, bet, mines, opened, multiplier) VALUES (?, ?, ?, '[]', '[]', 1.0)", (game_id, str(user_id), bet))
                            await db.commit()
                        send_msg(peer_id, f"💣 Мины\nСтавка: {bet}$\n\nВыберите количество мин (2-8):", get_mines_count_kb(game_id), reply_to=msg.get('id'))
                    else:
                        send_msg(peer_id, "❌ Формат: /мины [ставка]", reply_to=msg.get('id'))

                elif text_lower.startswith(("/рулетка", "рулетка")):
                    if len(parts) >= 3: await process_roulette(user_id, peer_id, parts[1], parts[-1], reply_to=msg.get('id'), is_ls=is_ls)
                    else: send_msg(peer_id, "❌ Формат: /рулетка красное 500", reply_to=msg.get('id'))
                
                elif text_lower.startswith(("/фортуна", "фортуна")):
                    await process_fortune(user_id, peer_id, reply_to=msg.get('id'), is_ls=is_ls)
                
                elif text_lower.startswith(("/rps", "rps")):
                    if len(parts) == 3 and parts[2].isdigit():
                        bet, p_choice = int(parts[2]), parts[1]
                        if bet > balance or bet < 10: send_msg(peer_id, f"❌ Мин. ставка 10, у тебя {balance}$", reply_to=msg.get('id'))
                        elif p_choice not in ["камень", "ножницы", "бумага"]: send_msg(peer_id, "❌ Выбери: камень, ножницы или бумага.", reply_to=msg.get('id'))
                        else:
                            b_choice = random.choice(["камень", "ножницы", "бумага"])
                            if p_choice == b_choice: res = f"🤝 Ничья! Бот выбрал {b_choice}."
                            elif (p_choice == "камень" and b_choice == "ножницы") or (p_choice == "ножницы" and b_choice == "бумага") or (p_choice == "бумага" and b_choice == "камень"):
                                await update_balance(user_id, bet); res = f"🎉 Ты победил! Бот выбрал {b_choice}. +{bet}$"
                            else:
                                await update_balance(user_id, -bet); res = f"😔 Ты проиграл. Бот выбрал {b_choice}. -{bet}$"
                            send_msg(peer_id, res + f"\nБаланс: {await get_balance(user_id)}$", keyboard=get_main_kb() if is_ls else None, reply_to=msg.get('id'))
                    else: send_msg(peer_id, "❌ Формат: /rps камень 500", reply_to=msg.get('id'))

                elif text_lower.startswith(("/duel", "duel")):
                    if len(parts) == 2 and parts[1].isdigit():
                        bet = int(parts[1])
                        if msg.get('reply_message'):
                            target_id = msg['reply_message']['from_id']
                            if target_id == user_id: send_msg(peer_id, "❌ Нельзя дуэлиться с собой.", reply_to=msg.get('id'))
                            else:
                                send_msg(peer_id, f"⚔️ [id{user_id}|Игрок] вызывает [id{target_id}|Игрока] на дуэль на {bet}$!\nЦель, напиши /принять.", reply_to=msg.get('id'))
                                async with aiosqlite.connect(DB_NAME) as db:
                                    await db.execute("CREATE TABLE IF NOT EXISTS duels (peer_id TEXT PRIMARY KEY, challenger TEXT, target TEXT, bet INTEGER)")
                                    await db.execute("REPLACE INTO duels (peer_id, challenger, target, bet) VALUES (?, ?, ?, ?)", (str(peer_id), str(user_id), str(target_id), bet))
                                    await db.commit()
                        else: send_msg(peer_id, "❌ Ответь (реплаем) на сообщение того, кого вызываешь.", reply_to=msg.get('id'))
                    else: send_msg(peer_id, "❌ Формат: /duel 500", reply_to=msg.get('id'))
                
                elif text_lower in ["/принять", "принять"]:
                    async with aiosqlite.connect(DB_NAME) as db:
                        async with db.execute("SELECT challenger, target, bet FROM duels WHERE peer_id = ?", (str(peer_id),)) as cursor:
                            row = await cursor.fetchone()
                            if row:
                                challenger, target, bet = row
                                if target == str(user_id):
                                    if await get_balance(user_id) < bet or await get_balance(challenger) < bet: send_msg(peer_id, "❌ У кого-то из вас не хватает денег.", reply_to=msg.get('id'))
                                    else:
                                        winner = random.choice([user_id, int(challenger)])
                                        loser = int(challenger) if winner == user_id else user_id
                                        await update_balance(winner, bet); await update_balance(loser, -bet)
                                        send_msg(peer_id, f"⚔️ Дуэль окончена! Победил [id{winner}|Игрок] и забрал {bet}$!", reply_to=msg.get('id'))
                                    await db.execute("DELETE FROM duels WHERE peer_id = ?", (str(peer_id),)); await db.commit()

                elif text_lower in ["/профиль", "профиль"]:
                    send_msg(peer_id, f"👤 Твой профиль:\n💰 Баланс: {balance}$\n🆔 ID: {user_id}", keyboard=get_main_kb() if is_ls else None, reply_to=msg.get('id'))
                
                elif text_lower in ["/топ", "топ"]:
                    async with aiosqlite.connect(DB_NAME) as db:
                        async with db.execute("SELECT user_id, balance FROM users ORDER BY balance DESC LIMIT 5") as cursor:
                            top = await cursor.fetchall()
                    top_text = "🏆 Топ 5:\n" + "\n".join([f"{i}. [id{u}|Игрок] — {b}$" for i, (u, b) in enumerate(top, 1)])
                    send_msg(peer_id, top_text, keyboard=get_main_kb() if is_ls else None, reply_to=msg.get('id'))

                elif text_lower.startswith(("/создать", "создать")) and user_id == ADMIN_ID:
                    try:
                        _, code, amount, limit = parts
                        async with aiosqlite.connect(DB_NAME) as db:
                            await db.execute("REPLACE INTO promos (code, amount, limit_count, used_by) VALUES (?, ?, ?, '')", (code, int(amount), int(limit)))
                            await db.commit()
                        send_msg(peer_id, f"✅ Промокод `{code}` на {amount}$ (Лимит: {limit}) создан!", reply_to=msg.get('id'))
                    except: send_msg(peer_id, "❌ Формат: /создать название сумма лимит", reply_to=msg.get('id'))
                
                elif text_lower.startswith(("/promo", "promo")):
                    try:
                        code = parts[1]
                        try: is_member = vk.groups.isMember(group_id=GROUP_ID, user_id=user_id)
                        except: is_member = 0
                        
                        if is_member == 0:
                            send_msg(peer_id, "❌ Ошибка, чтобы активировать промокод нужен быть подписан на сообщество", keyboard=get_sub_kb(), reply_to=msg.get('id')); continue
                        
                        async with aiosqlite.connect(DB_NAME) as db:
                            async with db.execute("SELECT amount, limit_count, used_by FROM promos WHERE code = ?", (code,)) as cursor:
                                row = await cursor.fetchone()
                                if not row: send_msg(peer_id, "❌ Промокод не существует или истекло промо.", reply_to=msg.get('id')); continue
                                amount, limit, used_by_str = row
                                used_by = used_by_str.split(",") if used_by_str else []
                                
                                if len(used_by) >= limit:
                                    await db.execute("DELETE FROM promos WHERE code = ?", (code,)); await db.commit()
                                    send_msg(peer_id, "❌ Истекло промо. Лимит активаций закончился.", reply_to=msg.get('id')); continue
                                if str(user_id) in used_by:
                                    send_msg(peer_id, "❌ Ты уже активировал этот промокод!", reply_to=msg.get('id')); continue
                                
                                used_by.append(str(user_id))
                                await db.execute("UPDATE promos SET used_by = ? WHERE code = ?", (",".join(used_by), code))
                                await db.commit()
                                await update_balance(user_id, amount)
                                send_msg(peer_id, f"✅ Промокод активирован! +{amount}$\nОсталось активаций: {limit - len(used_by)}", reply_to=msg.get('id'))
                    except: send_msg(peer_id, "❌ Формат: /promo код", reply_to=msg.get('id'))

        except Exception as e:
            print(f"⚠️ Ошибка в цикле: {e}")

if __name__ == "__main__":
    asyncio.run(main())
