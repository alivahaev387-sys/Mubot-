import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
import random

# ===== ТОКЕН И ID =====
TOKEN = "vk1.a.Fgowv-iH2wbOXG7ra56zmUWabQJy2OBRma9n4V3ufueJ_FJrbt5K_t9dOu_OtC-xF1iTWBi8yX5bGOmQ1kbQExof1U4IZKgoO6NVGNg9aaR17ECXar65GK6s-LdkflKto0qhZddvXHeDhxkFeya3z5XN80QnNGB7F676pFOs4xScHkUyvyvodMk5QsFpDHSrJ45m23CVzidcr1reHfrqW5ci9FxMDEhiF3JGG1021qQ"
GROUP_ID = 243089386

vk_session = vk_api.VkApi(token=TOKEN)
longpoll = VkBotLongPoll(vk_session, GROUP_ID)
vk = vk_session.get_api()

print("ТЕСТОВЫЙ БОТ ОТВЕЧАЕТ НА ВСЁ!")

while True:
    try:
        for event in longpoll.listen():
            if event.type == VkBotEventType.MESSAGE_NEW and event.object.message.get('text'):
                msg = event.object.message
                peer_id = msg['peer_id']
                msg_id = msg.get('id')
                
                # Отвечаем ТОЛЬКО в личных сообщениях (чтобы не спамить в беседах)
                if peer_id == msg['from_id']:
                    try:
                        vk.messages.send(
                            peer_id=peer_id,
                            message="Спасибо, что выбрали именно наш бот!\nВведите /help",
                            random_id=random.randint(1, 2**31 - 1),
                            reply_to=msg_id
                        )
                    except Exception as e:
                        print(f"Ошибка отправки: {e}")

    except Exception as e:
        print(f"⚠️ Глобальная ошибка: {e}")
        time.sleep(2)
