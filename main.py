import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType

TOKEN = "vk1.a.pf7JbyYrLynnnpKIf_QqAcsog-fXR2Iqcvpow4ABPVY7svPOb9LYhr4GcvnI0MOUL3Fc3PEYjUt1mJX6Ie9qoYMU1LliLt_ezEH2pJ7rhllbd2sXngeQGl9bXZ-iwxJuJdm224tW4eDVlXy6VnzRgcMXzNcsFe-rzQszktiyOEwXmmX3FyMmtHPPbvmtaAxqbA5-YD4LpGhdChHHVO0QYArFLhxuAVKOLlyfAJeIdPs"
GROUP_ID = 242296265

vk_session = vk_api.VkApi(token=TOKEN)
longpoll = VkBotLongPoll(vk_session, GROUP_ID)
vk = vk_session.get_api()

print("ТЕСТОВЫЙ БОТ ЗАПУЩЕН!")

for event in longpoll.listen():
    if event.type == VkBotEventType.MESSAGE_NEW and event.object.message['text']:
        msg = event.object.message
        peer_id = msg['peer_id']
        text = msg['text'].lower()
        
        if "начать" in text or "start" in text:
            vk.messages.send(
                peer_id=peer_id,
                message="Привет! Я работаю!",
                random_id=0
            )
