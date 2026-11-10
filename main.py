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

DB_FILE = "database.json"
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f: return json.load(f)
    return {"users": {}, "promos": {}, "active_chats": []}

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=4)

db = load_db()
waiting_for_bet = {}

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
            [{"action": {"type": "text", "label": "💼 Работа"}, "color": "positive"}, {"action": {"type": "text", "label": "🎰 Казино"}, "color": "primary"}],
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

print("БОТ ЗАПУЩЕН! ЖДУ СООБЩЕНИЯ...")

while True:
    try:
        for event in longpoll.listen():
            if event.type == VkBotEventType.MESSAGE_NEW:
                msg = event.object.message
                user_id = msg['from_id']
                peer_id = msg['peer_id']
                text = msg.get('text', '').strip()
                text_lower = text.lower()
                
                # Если это ЛС и текста нет (нажата кнопка "Начать")
                if peer_id == user_id and not text:
                    send_msg(peer_id, f"👋 Привет! Твой баланс: {get_balance(user_id)}$\nВыбирай действие 👇", get_main_kb())
                    continue
                
                if not text: continue
                balance = get_balance(user_id)
                
                # Игры в ЛС
                if text_lower in ["начать", "start", "begin", "меню", "привет"]:
                    send_msg(peer_id, f"🎰 Твой баланс: {balance}$.\nВыбирай действие 👇", get_main_kb())
                elif text == "💼 Работа":
                    send_msg(peer_id, "Выбери работу:", get_work_kb())
                elif text == "🔙 Назад":
                    send_msg(peer_id, "Меню:", get_main_kb())
                elif text in ["🚕 Такси", "🎣 Рыбалка", "🏹 Охота"]:
                    earned = random.randint(200, 800)
                    update_balance(user_id, earned)
                    send_msg(peer_id, f"✅ Ты заработал {earned}$!\nБаланс: {get_balance(user_id)}$", get_work_kb())
                elif text == "🎰 Казино":
                    waiting_for_bet[user_id] = True
                    send_msg(peer_id, f"🎰 Введи сумму ставки (Баланс: {balance}$):")
                elif text == "👤 Профиль":
                    send_msg(peer_id, f"👤 Баланс: {balance}$", get_main_kb())
                elif text == "🏆 Топ":
                    top = sorted(db["users"].items(), key=lambda x: x[1], reverse=True)[:5]
                    top_text = "🏆 Топ:\n" + "\n".join([f"{i}. ID {u} — {b}$" for i, (u, b) in enumerate(top, 1)])
                    send_msg(peer_id, top_text, get_main_kb())
                elif text == "📖 Помощь":
                    send_msg(peer_id, "📖 Жми кнопки! Промокод: /promo код", get_main_kb())
                elif user_id in waiting_for_bet:
                    if text.isdigit():
                        bet = int(text)
                        del waiting_for_bet[user_id]
                        if bet > balance or bet < 10:
                            send_msg(peer_id, f"❌ Мин. ставка 10$, у тебя {balance}$", get_main_kb())
                        else:
                            res = random.randint(0, 36)
                            if res % 2 != 0 and res != 0:
                                update_balance(user_id, bet)
                                send_msg(peer_id, f"🎉 Победа! Выпало {res} 🔴. +{bet}$", get_main_kb())
                            else:
                                update_balance(user_id, -bet)
                                send_msg(peer_id, f"😔 Проигрыш. Выпало {res} ⚫. -{bet}$", get_main_kb())
                    else:
                        send_msg(peer_id, "❌ Введи число!", get_main_kb())

    except Exception as e:
        print(f"Ошибка: {e}")
        time.sleep(1)
