import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
import json, random, time, threading

# ===== ТОКЕН И ID =====
TOKEN = "vk1.a.Fgowv-iH2wbOXG7ra56zmUWabQJy2OBRma9n4V3ufueJ_FJrbt5K_t9dOu_OtC-xF1iTWBi8yX5bGOmQ1kbQExof1U4IZKgoO6NVGNg9aaR17ECXar65GK6s-LdkflKto0qhZddvXHeDhxkFeya3z5XN80QnNGB7F676pFOs4xScHkUyvyvodMk5QsFpDHSrJ45m23CVzidcr1reHfrqW5ci9FxMDEhiF3JGG1021qQ"
GROUP_ID = 243089386

vk_session = vk_api.VkApi(token=TOKEN)
longpoll = VkBotLongPoll(vk_session, GROUP_ID)
vk = vk_session.get_api()

# Хранилище балансов в памяти (чтобы не зависало из-за базы данных)
balances = {}
active_chats = set()
waiting_for_bet = {}

def get_balance(user_id):
    return balances.get(user_id, 1000)

def set_balance(user_id, amount):
    balances[user_id] = amount

def send_msg(peer_id, message, reply_to=None):
    try:
        params = {
            'peer_id': peer_id,
            'message': message,
            'random_id': random.randint(1, 2**31 - 1)
        }
        if reply_to: 
            params['reply_to'] = reply_to
        return vk.messages.send(**params)
    except Exception as e:
        print(f"Ошибка отправки: {e}")

def get_activate_kb():
    return json.dumps({
        "inline": True,
        "buttons": [
            [{"action": {"type": "callback", "label": "🎮 Активировать", "payload": json.dumps({"cmd": "activate"})}, "color": "positive"}]
        ]
    }, ensure_ascii=False)

print("БОТ ЗАПУЩЕН (ЛЕГКАЯ ВЕРСИЯ)!")

while True:
    try:
        for event in longpoll.listen():
            
            # Приглашение в беседу
            if event.type == VkBotEventType.MESSAGE_NEW and event.object.message.get('action'):
                action = event.object.message['action']
                if action.get('type') == 'chat_invite_user' and action.get('member_id') == -GROUP_ID:
                    peer_id = event.object.message['peer_id']
                    text = ("Привет! Я игровой бот.\n\n"
                            "Чтобы включить игры, нажми на кнопку ниже.")
                    send_msg(peer_id, text, get_activate_kb())
                    continue

            # Обработка нажатия кнопки
            if event.type == VkBotEventType.MESSAGE_EVENT:
                payload = event.object.payload
                user_id = event.object.user_id
                peer_id = event.object.peer_id
                event_id = event.object.event_id
                
                if payload.get("cmd") == "activate":
                    active_chats.add(peer_id)
                    vk.messages.sendMessageEventAnswer(event_id=event_id, user_id=user_id, peer_id=peer_id, event_data=json.dumps({"type": "show_snackbar", "text": "✅ Успешно!"}))
                    send_msg(peer_id, "✅ Бот активирован в беседе!\nПиши /help.")
                continue

            # Текстовые сообщения
            if event.type == VkBotEventType.MESSAGE_NEW and event.object.message.get('text'):
                msg = event.object.message
                peer_id = msg['peer_id']
                user_id = msg['from_id'] 
                msg_id = msg.get('id')
                text = msg.get('text', '').strip().lower()
                
                is_chat = peer_id > 2000000000

                # Игнорируем беседы, где бот не активирован
                if is_chat and peer_id not in active_chats:
                    continue

                balance = get_balance(user_id)

                # Ожидание ставки
                if user_id in waiting_for_bet:
                    game_data = waiting_for_bet[user_id]
                    game_type = game_data["game"]
                    choice = game_data.get("choice", None)
                    
                    if text in ["отмена", "назад"]:
                        del waiting_for_bet[user_id]
                        send_msg(peer_id, "Ставка отменена.", reply_to=msg_id)
                        continue
                        
                    try:
                        if text in ["всё", "все", "all"]:
                            bet_amount = balance
                        else:
                            bet_amount = int(text)
                    except ValueError:
                        send_msg(peer_id, "❌ Введи число или 'всё'.", reply_to=msg_id)
                        continue

                    if bet_amount < 10:
                        send_msg(peer_id, "❌ Мин. ставка — 10.", reply_to=msg_id)
                        continue
                    if bet_amount > balance:
                        send_msg(peer_id, f"❌ Нет денег! Баланс: {balance}", reply_to=msg_id)
                        continue

                    del waiting_for_bet[user_id]
                    
                    if game_type in ["color", "parity"]:
                        result_num = random.randint(0, 36)
                        is_even = (result_num % 2 == 0) and result_num != 0
                        is_red = result_num in [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]
                        
                        color_emoji = "🔴" if is_red else ("⚫" if result_num != 0 else "🟢")
                        num_text = "ЗЕРО (0)" if result_num == 0 else f"{result_num} {color_emoji}"
                        
                        win = False
                        if game_type == "color":
                            if choice == "red" and is_red: win = True
                            if choice == "black" and not is_red and result_num != 0: win = True
                        elif game_type == "parity":
                            if choice == "even" and is_even: win = True
                            if choice == "odd" and not is_even and result_num != 0: win = True
                                
                        if win:
                            set_balance(user_id, balance + bet_amount)
                            res_text = f"🎉 ПОБЕДА!\n\nВыпало: {num_text}\nТы выиграл {bet_amount} монет!"
                        else:
                            set_balance(user_id, balance - bet_amount)
                            res_text = f"😔 ПРОИГРЫШ!\n\nВыпало: {num_text}\nТы потерял {bet_amount} монет."
                        send_msg(peer_id, res_text, reply_to=msg_id)

                    elif game_type == "drim":
                        result_num = random.randint(1, 15)
                        if result_num == choice:
                            set_balance(user_id, balance + bet_amount * 10)
                            res_text = f"🔥 ДЖЕКПОТ! 🔥\n\nВыпало: {result_num}\nТы выиграл x10: +{bet_amount * 10} монет!"
                        else:
                            set_balance(user_id, balance - bet_amount)
                            res_text = f"😔 ПРОИГРЫШ!\n\nВыпало: {result_num}\nТы потерял {bet_amount} монет."
                        send_msg(peer_id, res_text, reply_to=msg_id)
                    
                    elif game_type == "rps":
                        bot_choice = random.choice(["камень", "ножницы", "бумага"])
                        win = False
                        draw = False
                        if choice == bot_choice: draw = True
                        elif (choice == "камень" and bot_choice == "ножницы") or \
                             (choice == "ножницы" and bot_choice == "бумага") or \
                             (choice == "бумага" and bot_choice == "камень"): win = True
                             
                        if draw:
                            res_text = f"🤝 НИЧЬЯ!\n\nТы: {choice}\nБот: {bot_choice}"
                        elif win:
                            set_balance(user_id, balance + bet_amount)
                            res_text = f"🎉 ПОБЕДА!\n\nТы: {choice}\nБот: {bot_choice}\nТы выиграл {bet_amount} монет!"
                        else:
                            set_balance(user_id, balance - bet_amount)
                            res_text = f"😔 ПРОИГРЫШ!\n\nТы: {choice}\nБот: {bot_choice}\nТы потерял {bet_amount} монет."
                        send_msg(peer_id, res_text, reply_to=msg_id)
                    continue

                # Команды
                if text == "/help" or text == "помощь":
                    help_text = ("📖 Команды:\n\n"
                                 "🎰 /казино\n"
                                 "🔴 /красное или /черное\n"
                                 "🟢 /чет или /нечет\n"
                                 "🔢 /дрим [1-15] (x10)\n"
                                 "✂️ /rps [камень/ножницы/бумага]\n"
                                 "⚔️ /duel @игрок [сумма]\n\n"
                                 "👤 /профиль\n"
                                 "🏆 /топ")
                    send_msg(peer_id, help_text, reply_to=msg_id)
                
                elif text in ["начать", "start", "меню"]:
                    send_msg(peer_id, "🎰 Твой баланс: " + str(balance) + " монет.\nВведи /help.", reply_to=msg_id)
                
                elif text == "/казино":
                    send_msg(peer_id, "🎰 Игры:\n/красное\n/черное\n/чет\n/нечет\n/дрим [1-15]\n/rps [камень/ножницы/бумага]", reply_to=msg_id)
                
                elif text == "/красное":
                    waiting_for_bet[user_id] = {"game": "color", "choice": "red"}
                    send_msg(peer_id, "🔴 Выбрано Красное. Напиши сумму ставки:", reply_to=msg_id)
                elif text == "/черное":
                    waiting_for_bet[user_id] = {"game": "color", "choice": "black"}
                    send_msg(peer_id, "⚫ Выбрано Черное. Напиши сумму ставки:", reply_to=msg_id)
                elif text == "/чет":
                    waiting_for_bet[user_id] = {"game": "parity", "choice": "even"}
                    send_msg(peer_id, "🟢 Выбран Чет. Напиши сумму ставки:", reply_to=msg_id)
                elif text == "/нечет":
                    waiting_for_bet[user_id] = {"game": "parity", "choice": "odd"}
                    send_msg(peer_id, "🔴 Выбран Нечет. Напиши сумму ставки:", reply_to=msg_id)
                elif text.startswith("/дрим"):
                    parts = text.split()
                    if len(parts) == 2 and parts[1].isdigit() and 1 <= int(parts[1]) <= 15:
                        waiting_for_bet[user_id] = {"game": "drim", "choice": int(parts[1])}
                        send_msg(peer_id, f"🔢 Выбрано число {parts[1]}. Напиши сумму ставки:", reply_to=msg_id)
                    else:
                        send_msg(peer_id, "❌ Напиши: /дрим 7 (от 1 до 15).", reply_to=msg_id)
                elif text.startswith("/rps"):
                    parts = text.split()
                    if len(parts) == 2 and parts[1] in ["камень", "ножницы", "бумага"]:
                        waiting_for_bet[user_id] = {"game": "rps", "choice": parts[1]}
                        send_msg(peer_id, f"✂️ Ты выбрал: {parts[1]}. Напиши сумму ставки:", reply_to=msg_id)
                    else:
                        send_msg(peer_id, "❌ Напиши: /rps камень (или ножницы, бумага).", reply_to=msg_id)
                
                elif "профиль" in text or "/профиль" in text:
                    send_msg(peer_id, f"👤 Профиль:\n💰 Баланс: {balance} монет", reply_to=msg_id)
                
                elif "топ" in text or "/топ" in text:
                    send_msg(peer_id, "🏆 Топ игроков находится в разработке.", reply_to=msg_id)
                
                else:
                    send_msg(peer_id, "Спасибо, что выбрали именно наш бот!\nВведите /help", reply_to=msg_id)

    except Exception as e:
        print(f"⚠️ Ошибка: {e}")
        time.sleep(2)
