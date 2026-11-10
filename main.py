import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
import json, random

TOKEN = "vk1.a.n-y1VnQMFI87cAGH7zXHwYy6LncLM_UuAaCihe6dlWxUBLGwS8no-KjRmFrA9zmwy-STfP7f2VZOHArq1-WVKYVRUA3H1F3-pO5gtXRxEziw3u3st-dTYHNiK_an2ZcbUIpXYNy98HHTGQv12wFtMLsSASQ0kO0ke0B0DRsXc7hn-LQrYcpbu54a_kQmP7dxBO5a8gTmuS9Dn9LH7oMLfE6G6_GPJZxJAgkwzptCnWw"
GROUP_ID = 243089386

vk_session = vk_api.VkApi(token=TOKEN)
longpoll = VkBotLongPoll(vk_session, GROUP_ID)
vk = vk_session.get_api()

# Простейшая база
balance = {}

def get_bal(uid):
    return balance.get(uid, 1000)

def get_kb():
    return json.dumps({
        "one_time": False, 
        "buttons": [
            [{"action": {"type": "text", "label": "💼 Работа"}, "color": "positive"}, {"action": {"type": "text", "label": "🎰 Казино"}, "color": "primary"}],
            [{"action": {"type": "text", "label": "👤 Профиль"}, "color": "secondary"}]
        ]
    }, ensure_ascii=False)

print("БОТ ЗАПУЩЕН! ЖДУ ЛЮБОЕ СООБЩЕНИЕ...")

for event in longpoll.listen():
    if event.type == VkBotEventType.MESSAGE_NEW:
        msg = event.object.message
        uid = msg['from_id']
        peer_id = msg['peer_id']
        text = msg.get('text', '')
        
        # Отправляем меню на ЛЮБОЕ сообщение в ЛС
        if peer_id == uid:
            if text == "💼 Работа":
                earned = random.randint(500, 1500)
                balance[uid] = get_bal(uid) + earned
                vk.messages.send(peer_id=peer_id, message=f"Ты заработал {earned}$! Баланс: {balance[uid]}$", random_id=0, keyboard=get_kb())
            elif text == "👤 Профиль":
                vk.messages.send(peer_id=peer_id, message=f"Твой баланс: {get_bal(uid)}$", random_id=0, keyboard=get_kb())
            else:
                # Это сработает на кнопку "Начать", на "Привет" и на любую букву
                vk.messages.send(peer_id=peer_id, message=f"Привет! Твой баланс: {get_bal(uid)}$. Жми кнопки!", random_id=0, keyboard=get_kb())
