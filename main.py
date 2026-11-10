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

# ===== БАЗА ДАННЫХ =====
DB_FILE = "database.json"
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f: return json.load(f)
    return {"users": {}, "promos": {}, "active_chats": []}

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

def get_main_kb():
    return json.dumps({
        "one_time": False, 
        "buttons": [
            [{"action": {"type": "text", "label": "💼 Работа"}, "color": "positive"}, {"action": {"type": "text", "label": "🎰 Рулетка"}, "color": "primary"}],
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

# ===== ФУНКЦИЯ РУЛЕТКИ =====
def process_roulette(user_id, peer_id, choice, bet_str, reply_to=None):
    balance = get_balance(user_id)
    bet_str_clean = bet_str.lower().replace("ё", "е")
    
    if bet_str_clean in ["вб", "всё", "все"]:
        bet = balance
    elif bet_str_clean.isdigit():
        bet = int(bet_str_clean)
    elif "к" in bet_str_clean and bet_str_clean.replace("к", "").isdigit():
        bet = int(bet_str_clean.replace("к", "")) * 1000
    else:
        send_msg(peer_id, "❌ Неверная ставка. Введи число, '1кк' или 'вб'", reply_to=reply_to)
        return

    if bet < 10 and bet != balance:
        send_msg(peer_id, "❌ Минимальная ставка 10$", reply_to=reply_to)
        return
    if bet > balance:
        send_msg(peer_id, f"❌ У тебя нет столько денег! Баланс: {balance}$", reply_to=reply_to)
        return

    res = random.randint(0, 36)
    red_numbers = [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]
    
    win = False
    win_multiplier = 2
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
    elif choice == "1-12":
        if 1 <= res <= 12: win = True; win_multiplier = 3
    elif choice == "13-24":
        if 13 <= res <= 24: win = True; win_multiplier = 3
    elif choice == "25-36":
        if 25 <= res <= 36: win = True; win_multiplier = 3
    elif choice == "1-18":
        if 1 <= res <= 18: win = True
    elif choice == "19-36":
        if 19 <= res <= 36: win = True
    else:
        send_msg(peer_id, "❌ Я не понял, на что ставим. Напиши: красное, черное, чет, нечет, или число.", reply_to=reply_to)
        return

    color_emoji = "🔴" if res in red_numbers else "⚫" if res != 0 else "🟢"
    
    if win:
        win_amount = bet * win_multiplier
        update_balance(user_id, win_amount)
        msg = f"🎉 ПОБЕДА! Выпало {res} {color_emoji}\nТы выиграл {win_amount}$\nБаланс: {get_balance(user_id)}$"
    else:
        update_balance(user_id, -bet)
        msg = f"😔 ПРОИГРЫШ. Выпало {res} {color_emoji}\nТы потерял {bet}$\nБаланс: {get_balance(user_id)}$"

    send_msg(peer_id, msg, get_main_kb(), reply_to=reply_to)

# ===== ЗАПУСК =====
print("БОТ ЗАПУЩЕН! ТЕСТ РУЛЕТКИ.")

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
                    send_msg(peer_id, f"👋 Привет! Твой баланс: {get_balance(user_id)}$\nВыбирай действие 👇", get_main_kb())
                    continue
                
                if not text: continue
                balance = get_balance(user_id)

                # === ЛС ===
                if is_ls:
                    if text_lower in ["начать", "start", "меню", "привет"]:
                        send_msg(peer_id, f"🎰 Твой баланс: {balance}$\nВыбирай действие 👇", get_main_kb())
                    elif text == "💼 Работа":
                        send_msg(peer_id, "Выбери работу:", get_work_kb())
                    elif text == "🔙 Назад":
                        send_msg(peer_id, "Меню:", get_main_kb())
                    elif text in ["🚕 Такси", "🎣 Рыбалка", "🏹 Охота"]:
                        earned = random.randint(200, 800)
                        update_balance(user_id, earned)
                        send_msg(peer_id, f"✅ Ты заработал {earned}$!\n💰 Баланс: {get_balance(user_id)}$", get_work_kb())
                    
                    elif text == "🎰 Рулетка" or text_lower == "рулетка":
                        rules_text = (
                            "Как играть в рулетку ❓\n\n"
                            "«Рулетка [на что ставишь] [ставка]»\n"
                            "▪️ Число от 0 до 36 (x36)\n"
                            "▪️ Чет (x2)\n"
                            "▪️ Нечет (x2)\n"
                            "▪️ Красное (x2)\n"
                            "▪️ Черное (x2)\n"
                            "▪️ 1-12 (x3)\n"
                            "▪️ 13-24 (x3)\n"
                            "▪️ 25-36 (x3)\n"
                            "▪️ 1-18 (x2)\n"
                            "▪️ 19-36 (x2)\n\n"
                            "⚠️ Чтобы поставить весь баланс, там где ставка пиши «вб»\n\n"
                            "Пример — «Рулетка чет 1кк»"
                        )
                        send_msg(peer_id, rules_text, get_main_kb())

                    # ЖЕСТКАЯ ПРОВЕРКА КОМАНДЫ (Ловит и "Рулетка", и "Рул")
                    elif text_lower.startswith(("рулетка ", "рул ")):
                        parts = text_lower.replace("/", "").split()
                        if len(parts) >= 3:
                            bet_str = parts[-1]
                            choice = " ".join(parts[1:-1])
                            process_roulette(user_id, peer_id, choice, bet_str, reply_to=msg.get('id'))
                        else:
                            send_msg(peer_id, "❌ Формат: Рулетка красное 5000", get_main_kb())

                    elif text == "👤 Профиль":
                        send_msg(peer_id, f"👤 Твой профиль:\n💰 Баланс: {balance}$\n🆔 ID: {user_id}", get_main_kb())
                    elif text == "🏆 Топ":
                        top = sorted(db["users"].items(), key=lambda x: x[1], reverse=True)[:5]
                        top_text = "🏆 Топ 5:\n" + "\n".join([f"{i}. ID {u} — {b}$" for i, (u, b) in enumerate(top, 1)])
                        send_msg(peer_id, top_text, get_main_kb())
                    elif text == "📖 Помощь":
                        send_msg(peer_id, "📖 Жми кнопки! Промокод: /promo [код]", get_main_kb())

                # === БЕСЕДЫ ===
                else:
                    if text_lower.startswith(("/рулетка ", "/рул ")):
                        parts = text_lower.replace("/", "").split()
                        if len(parts) >= 3:
                            bet_str = parts[-1]
                            choice = " ".join(parts[1:-1])
                            process_roulette(user_id, peer_id, choice, bet_str, reply_to=msg.get('id'))

    except Exception as e:
        print(f"⚠️ Ошибка: {e}")
        time.sleep(2)
