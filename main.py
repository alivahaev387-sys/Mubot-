import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
import json, random, time, os

# ===== НАСТРОЙКИ =====
TOKEN = "vk1.a.n-y1VnQMFI87cAGH7zXHwYy6LncLM_UuAaCihe6dlWxUBLGwS8no-KjRmFrA9zmwy-STfP7f2VZOHArq1-WVKYVRUA3H1F3-pO5gtXRxEziw3u3st-dTYHNiK_an2ZcbUIpXYNy98HHTGQv12wFtMLsSASQ0kO0ke0B0DRsXc7hn-LQrYcpbu54a_kQmP7dxBO5a8gTmuS9Dn9LH7oMLfE6G6_GPJZxJAgkwzptCnWw"
GROUP_ID = 243089386
ADMIN_ID = 200005093141 
FORTUNA_CD = 600  # 10 минут

vk_session = vk_api.VkApi(token=TOKEN)
longpoll = VkBotLongPoll(vk_session, GROUP_ID)
vk = vk_session.get_api()

# ===== БАЗА ДАННЫХ =====
DB_FILE = "database.json"
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f: 
            data = json.load(f)
            if "fortune_cd" not in data: data["fortune_cd"] = {}
            return data
    return {"users": {}, "promos": {}, "active_chats": [], "active_duel": {}, "fortune_cd": {}}

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=4)

db = load_db()

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
def get_work_kb():
    return json.dumps({
        "one_time": False, 
        "buttons": [
            [{"action": {"type": "text", "label": "🚕 Такси"}, "color": "primary"}, {"action": {"type": "text", "label": "🎣 Рыбалка"}, "color": "primary"}],
            [{"action": {"type": "text", "label": "🏹 Охота"}, "color": "primary"}, {"action": {"type": "text", "label": "🔙 Назад"}, "color": "secondary"}]
        ]
    }, ensure_ascii=False)

def get_main_kb():
    return json.dumps({
        "one_time": False, 
        "buttons": [
            [{"action": {"type": "text", "label": "💼 Работа"}, "color": "positive"}],
            [{"action": {"type": "text", "label": "📖 Помощь"}, "color": "secondary"}]
        ]
    }, ensure_ascii=False)

def get_sub_kb():
    return json.dumps({
        "inline": True,
        "buttons": [
            [{"action": {"type": "open_link", "link": f"https://vk.com/public{GROUP_ID}", "label": "📢 Подписаться"}}]
        ]
    }, ensure_ascii=False)

# ===== ЛОГИКА ИГР =====
def process_roulette(user_id, peer_id, choice, bet_str, reply_to=None, is_ls=False):
    balance = get_balance(user_id)
    bet_str_clean = bet_str.lower().replace("ё", "е")
    
    if bet_str_clean in ["вб", "всё", "все"]: bet = balance
    elif bet_str_clean.isdigit(): bet = int(bet_str_clean)
    elif "к" in bet_str_clean and bet_str_clean.replace("к", "").isdigit(): bet = int(bet_str_clean.replace("к", "")) * 1000
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
        update_balance(user_id, win_amount)
        msg = f"🎉 ПОБЕДА! Выпало {res} {color_emoji}\nТы выиграл {win_amount}$\nБаланс: {get_balance(user_id)}$"
    else:
        update_balance(user_id, -bet)
        msg = f"😔 ПРОИГРЫШ. Выпало {res} {color_emoji}\nТы потерял {bet}$\nБаланс: {get_balance(user_id)}$"
        
    kb = get_main_kb() if is_ls else None
    send_msg(peer_id, msg, keyboard=kb, reply_to=reply_to)

def process_fortune(user_id, peer_id, reply_to=None, is_ls=False):
    uid = str(user_id)
    current_time = int(time.time())
    
    last_use = db["fortune_cd"].get(uid, 0)
    if current_time - last_use < FORTUNA_CD:
        remaining = FORTUNA_CD - (current_time - last_use)
        minutes = remaining // 60
        seconds = remaining % 60
        msg = f"⏳ Следующая фортуна будет доступна через {minutes} мин. {seconds} сек."
        kb = get_main_kb() if is_ls else None
        send_msg(peer_id, msg, keyboard=kb, reply_to=reply_to)
        return

    balance = get_balance(user_id)
    if balance < 100: 
        send_msg(peer_id, "❌ Фортуна стоит 100$. У тебя мало денег.", reply_to=reply_to); return
    
    update_balance(user_id, -100)
    db["fortune_cd"][uid] = current_time
    save_db(db)
    
    prizes = [0, 50, 100, 200, 500, 1000, 5000]
    prize = random.choice(prizes)
    update_balance(user_id, prize)
    msg = f"🎰 Крутим фортуну...\nВыпало: {prize}$!\nБаланс: {get_balance(user_id)}$"
    
    kb = get_main_kb() if is_ls else None
    send_msg(peer_id, msg, keyboard=kb, reply_to=reply_to)

# ===== ЗАПУСК =====
print("БОТ ЗАПУЩЕН! ПРОВЕРКА ПОДПИСКИ ВКЛЮЧЕНА.")

while True:
    try:
        for event in longpoll.listen():
            if event.type == VkBotEventType.MESSAGE_NEW:
                msg = event.object.message
                user_id = msg['from_id']
                peer_id = msg['peer_id']
                text = msg.get('text', '').strip()
                text_lower = text.lower()
                is_ls = (peer_id == user_id)
                
                if is_ls and not text:
                    send_msg(peer_id, f"👋 Привет! Твой баланс: {get_balance(user_id)}$\nЖми «Работа» или пиши /help", get_main_kb())
                    continue
                
                if not text: continue
                balance = get_balance(user_id)
                parts = text_lower.replace("/", "").split()

                if text_lower in ["/help", "help", "помощь", "📖 помощь"]:
                    help_text = (
                        "📖 **Игровые команды:**\n\n"
                        "🎰 /рулетка [цвет/чет] [ставка]\n"
                        "🎲 /фортуна - Крутить (100$)\n"
                        "✂️ /rps [камень/ножницы/бумага] [ставка]\n"
                        "⚔️ /duel [сумма] - Вызов (реплаем)\n"
                        "👤 /профиль - Твой баланс\n"
                        "🏆 /топ - Богачи\n"
                        "🎁 /promo [код] - Активировать (Нужна подписка!)"
                    )
                    kb = get_main_kb() if is_ls else None
                    send_msg(peer_id, help_text, keyboard=kb, reply_to=msg.get('id'))
                    continue

                if is_ls:
                    if text_lower in ["начать", "start", "меню", "привет"]:
                        send_msg(peer_id, f"🎰 Твой баланс: {balance}$\nЖми кнопку или пиши /help", get_main_kb())
                    elif text == "💼 Работа":
                        send_msg(peer_id, "Выбери работу:", get_work_kb())
                    elif text == "🔙 Назад":
                        send_msg(peer_id, "Меню:", get_main_kb())
                    elif text in ["🚕 Такси", "🎣 Рыбалка", "🏹 Охота"]:
                        earned = random.randint(200, 800)
                        update_balance(user_id, earned)
                        send_msg(peer_id, f"✅ Ты заработал {earned}$!\n💰 Баланс: {get_balance(user_id)}$", get_work_kb())

                if text_lower.startswith(("/рулетка", "рулетка")):
                    if len(parts) >= 3:
                        bet_str = parts[-1]
                        choice = parts[1]
                        process_roulette(user_id, peer_id, choice, bet_str, reply_to=msg.get('id'), is_ls=is_ls)
                    else:
                        send_msg(peer_id, "❌ Формат: /рулетка красное 500", reply_to=msg.get('id'))
                
                elif text_lower.startswith(("/фортуна", "фортуна")):
                    process_fortune(user_id, peer_id, reply_to=msg.get('id'), is_ls=is_ls)
                
                elif text_lower.startswith(("/rps", "rps")):
                    if len(parts) == 3 and parts[2].isdigit():
                        bet = int(parts[2])
                        if bet > balance or bet < 10:
                            send_msg(peer_id, f"❌ Мин. ставка 10, у тебя {balance}$", reply_to=msg.get('id'))
                        else:
                            player_choice = parts[1]
                            bot_choice = random.choice(["камень", "ножницы", "бумага"])
                            if player_choice not in ["камень", "ножницы", "бумага"]:
                                send_msg(peer_id, "❌ Выбери: камень, ножницы или бумага.", reply_to=msg.get('id'))
                            else:
                                if player_choice == bot_choice: msg_res = f"🤝 Ничья! Бот выбрал {bot_choice}."
                                elif (player_choice == "камень" and bot_choice == "ножницы") or (player_choice == "ножницы" and bot_choice == "бумага") or (player_choice == "бумага" and bot_choice == "камень"):
                                    update_balance(user_id, bet)
                                    msg_res = f"🎉 Ты победил! Бот выбрал {bot_choice}. +{bet}$"
                                else:
                                    update_balance(user_id, -bet)
                                    msg_res = f"😔 Ты проиграл. Бот выбрал {bot_choice}. -{bet}$"
                                kb = get_main_kb() if is_ls else None
                                send_msg(peer_id, msg_res + f"\nБаланс: {get_balance(user_id)}$", keyboard=kb, reply_to=msg.get('id'))
                    else:
                        send_msg(peer_id, "❌ Формат: /rps камень 500", reply_to=msg.get('id'))

                elif text_lower.startswith(("/duel", "duel")):
                    if len(parts) == 2 and parts[1].isdigit():
                        bet = int(parts[1])
                        if msg.get('reply_message'):
                            target_id = msg['reply_message']['from_id']
                            if target_id == user_id:
                                send_msg(peer_id, "❌ Нельзя дуэлиться с собой.", reply_to=msg.get('id'))
                            else:
                                send_msg(peer_id, f"⚔️ [id{user_id}|Игрок] вызывает [id{target_id}|Игрока] на дуэль на {bet}$!\nЦель, напиши /принять чтобы согласиться.", reply_to=msg.get('id'))
                                db["active_duel"] = {"challenger": user_id, "target": target_id, "bet": bet, "peer_id": peer_id}
                                save_db(db)
                        else:
                            send_msg(peer_id, "❌ Ответь (реплаем) на сообщение того, кого вызываешь.", reply_to=msg.get('id'))
                    else:
                        send_msg(peer_id, "❌ Формат: /duel 500 (реплаем на сообщение)", reply_to=msg.get('id'))
                
                elif text_lower in ["/принять", "принять"] and "active_duel" in db:
                    duel = db["active_duel"]
                    if duel["target"] == user_id and duel["peer_id"] == peer_id:
                        bet = duel["bet"]
                        if get_balance(user_id) < bet or get_balance(duel["challenger"]) < bet:
                            send_msg(peer_id, "❌ У кого-то из вас не хватает денег на дуэль.", reply_to=msg.get('id'))
                        else:
                            winner_id = random.choice([user_id, duel["challenger"]])
                            loser_id = duel["challenger"] if winner_id == user_id else user_id
                            update_balance(winner_id, bet)
                            update_balance(loser_id, -bet)
                            send_msg(peer_id, f"⚔️ Дуэль окончена! Победил [id{winner_id}|Игрок] и забрал {bet}$!", reply_to=msg.get('id'))
                        del db["active_duel"]
                        save_db(db)

                elif text_lower in ["/профиль", "профиль"]:
                    kb = get_main_kb() if is_ls else None
                    send_msg(peer_id, f"👤 Твой профиль:\n💰 Баланс: {balance}$\n🆔 ID: {user_id}", keyboard=kb, reply_to=msg.get('id'))
                
                elif text_lower in ["/топ", "топ"]:
                    top = sorted(db["users"].items(), key=lambda x: x[1], reverse=True)[:5]
                    top_text = "🏆 Топ 5:\n" + "\n".join([f"{i}. [id{u}|Игрок] — {b}$" for i, (u, b) in enumerate(top, 1)])
                    kb = get_main_kb() if is_ls else None
                    send_msg(peer_id, top_text, keyboard=kb, reply_to=msg.get('id'))

                elif text_lower.startswith(("/промокод", "промокод")) and user_id == ADMIN_ID:
                    try:
                        _, code, amount = parts
                        db["promos"][code] = int(amount)
                        save_db(db)
                        send_msg(peer_id, f"✅ Промокод `{code}` на {amount}$ создан!", reply_to=msg.get('id'))
                    except:
                        send_msg(peer_id, "❌ Формат: /промокод название сумма", reply_to=msg.get('id'))
                
                # === АКТИВАЦИЯ ПРОМОКОДА С ПРОВЕРКОЙ ПОДПИСКИ ===
                elif text_lower.startswith(("/promo", "promo")):
                    try:
                        code = parts[1]
                        
                        # Проверяем подписку через ВК API
                        try:
                            is_member = vk.groups.isMember(group_id=GROUP_ID, user_id=user_id)
                        except Exception as e:
                            print(f"Ошибка проверки подписки: {e}")
                            is_member = 0 # Если ошибка (нет прав), считаем, что не подписан
                        
                        if is_member == 0:
                            msg = "❌ Чтобы активировать промокод, вы должны быть подписаны на наше сообщество!"
                            # В ЛС и в беседе прикрепляем инлайн-кнопку подписки
                            send_msg(peer_id, msg, keyboard=get_sub_kb(), reply_to=msg.get('id'))
                            continue
                            
                        # Если подписан - активируем
                        if code in db["promos"]:
                            reward = db["promos"][code]
                            del db["promos"][code]
                            save_db(db)
                            update_balance(user_id, reward)
                            send_msg(peer_id, f"✅ Промокод активирован! +{reward}$", reply_to=msg.get('id'))
                        else:
                            send_msg(peer_id, "❌ Неверный промокод или он уже активирован.", reply_to=msg.get('id'))
                    except:
                        send_msg(peer_id, "❌ Формат: /promo код", reply_to=msg.get('id'))

    except Exception as e:
        print(f"⚠️ Ошибка: {e}")
        time.sleep(2)
