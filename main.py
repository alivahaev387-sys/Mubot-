import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType

TOKEN = "vk1.a.Fgowv-iH2wbOXG7ra56zmUWabQJy2OBRma9n4V3ufueJ_FJrbt5K_t9dOu_OtC-xF1iTWBi8yX5bGOmQ1kbQExof1U4IZKgoO6NVGNg9aaR17ECXar65GK6s-LdkflKto0qhZddvXHeDhxkFeya3z5XN80QnNGB7F676pFOs4xScHkUyvyvodMk5QsFpDHSrJ45m23CVzidcr1reHfrqW5ci9FxMDEhiF3JGG1021qQ"
GROUP_ID = 243089386

vk_session = vk_api.VkApi(token=TOKEN)
longpoll = VkBotLongPoll(vk_session, GROUP_ID)
vk = vk_session.get_api()

print("БОТ ЗАПУЩЕН!")

while True:
    try:
        for event in longpoll.listen():
            if event.type == VkBotEventType.MESSAGE_NEW and event.object.message.get('text'):
                msg = event.object.message
                peer_id = msg['peer_id']
                text = msg.get('text', '').lower().strip()
                
                if text in ["начать", "start", "/help"]:
                    vk.messages.send(
                        peer_id=peer_id,
                        message="Привет! Я работаю. (Это тест)",
                        random_id=0
                    )
    except Exception as e:
        print(f"ОШИБКА: {e}")
