import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType

TOKEN = "vk1.a.n-y1VnQMFI87cAGH7zXHwYy6LncLM_UuAaCihe6dlWxUBLGwS8no-KjRmFrA9zmwy-STfP7f2VZOHArq1-WVKYVRUA3H1F3-pO5gtXRxEziw3u3st-dTYHNiK_an2ZcbUIpXYNy98HHTGQv12wFtMLsSASQ0kO0ke0B0DRsXc7hn-LQrYcpbu54a_kQmP7dxBO5a8gTmuS9Dn9LH7oMLfE6G6_GPJZxJAgkwzptCnWw"
GROUP_ID = 243089386

vk_session = vk_api.VkApi(token=TOKEN)
longpoll = VkBotLongPoll(vk_session, GROUP_ID)
vk = vk_session.get_api()

print("ТЕСТОВЫЙ БОТ ЗАПУЩЕН!")

for event in longpoll.listen():
    if event.type == VkBotEventType.MESSAGE_NEW:
        msg = event.object.message
        print(f"Пришло сообщение от {msg['from_id']}: {msg.get('text')}")
        
        try:
            vk.messages.send(
                peer_id=msg['peer_id'],
                message="✅ Я работаю! Код доходит до ВК.",
                random_id=0
            )
        except Exception as e:
            print(f"Ошибка отправки: {e}")
