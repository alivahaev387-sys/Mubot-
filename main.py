import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType

# ===== ТОКЕН И ID =====
TOKEN = "vk1.a.Fgowv-iH2wbOXG7ra56zmUWabQJy2OBRma9n4V3ufueJ_FJrbt5K_t9dOu_OtC-xF1iTWBi8yX5bGOmQ1kbQExof1U4IZKgoO6NVGNg9aaR17ECXar65GK6s-LdkflKto0qhZddvXHeDhxkFeya3z5XN80QnNGB7F676pFOs4xScHkUyvyvodMk5QsFpDHSrJ45m23CVzidcr1reHfrqW5ci9FxMDEhiF3JGG1021qQ"
GROUP_ID = 243089386

# Подключение к ВК
vk_session = vk_api.VkApi(token=TOKEN)
longpoll = VkBotLongPoll(vk_session, GROUP_ID)
vk = vk_session.get_api()

print("ТЕСТОВЫЙ БОТ ЗАПУЩЕН!")

for event in longpoll.listen():
    if event.type == VkBotEventType.MESSAGE_NEW:
        msg = event.object.message
        peer_id = msg['peer_id']
        text = msg.get('text', '').lower()
        
        # Если бот получает сообщение "начать" или "start", он отвечает
        if "начать" in text or "start" in text:
            vk.messages.send(
                peer_id=peer_id,
                message="Привет! Связь установлена. Я работаю!",
                random_id=0,
                reply_to=msg.get('id') # Отвечаем реплаем на твое сообщение
            )
            print("Бот ответил на сообщение!")
