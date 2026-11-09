import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
import json, random, time

# ===== ТОКЕН И НАСТРОЙКИ =====
TOKEN = "vk1.a.Fgowv-iH2wbOXG7ra56zmUWabQJy2OBRma9n4V3ufueJ_FJrbt5K_t9dOu_OtC-xF1iTWBi8yX5bGOmQ1kbQExof1U4IZKgoO6NVGNg9aaR17ECXar65GK6s-LdkflKto0qhZddvXHeDhxkFeya3z5XN80QnNGB7F676pFOs4xScHkUyvyvodMk5QsFpDHSrJ45m23CVzidcr1reHfrqW5ci9FxMDEhiF3JGG1021qQ"
GROUP_ID = 243089386
ADMIN_ID = 200005093141 

vk_session = vk_api.VkApi(token=TOKEN)
longpoll = VkBotLongPoll(vk_session, GROUP_ID)
vk = vk_session.get_api()

# Хранилище в памяти (не может сломаться)
balances = {}

def get_balance(user_id):
    return balances.get(user_id, 1000)

def set_balance(user_id, amount):
    balances[user_id] = amount

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
        print(f"Ошибка отправки: {e}")

print("БОТ ЗАПУЩЕН!")

while True:
    try:
        for event in longpoll.listen():
            if event.type == VkBotEventType.MESSAGE_NEW and event.object.message.get('text'):
                msg = event.object.message
                peer_id = msg['peer_id']
                user_id = msg['from_id'] 
                msg_id = msg.get('id')
                text = msg.get('text', '').strip().lower()
                
                balance = get_balance(user_id)

                if text in ["начать", "start", "/help"]:
                    send_msg(peer_id, f"Привет! Бот работает.\nТвой баланс: {balance} монет.", reply_to=msg_id)
                
                elif text == "/профиль":
                    send_msg(peer_id, f"👤 Баланс: {balance} монет", reply_to=msg_id)
                
                elif text == "/такси":
                    earned = random.randint(50, 200)
                    set_balance(user_id, balance + earned)
                    send_msg(peer_id, f"🚕 Ты заработал {earned} монет на такси!", reply_to=msg_id)

    except Exception as e:
        print(f"⚠️ Ошибка: {e}")
        time.sleep(2)
