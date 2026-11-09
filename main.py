import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
import json, random, time

# ===== ТОКЕН И НАСТРОЙКИ =====
TOKEN = "vk1.a.Fgowv-iH2wbOXG7ra56zmUWabQJy2OBRma9n4V3ufueJ_FJrbt5K_t9dOu_OtC-xF1iTWBi8yX5bGOmQ1kbQExof1U4IZKgoO6NVGNg9aaR17ECXar65GK6s-LdkflKto0qhZddvXHeDhxkFeya3z5XN80QnNGB7F676pFOs4xScHkUyvyvodMk5QsFpDHSrJ45m23CVzidcr1reHfrqW5ci9FxMDEhiF3JGG1021qQ"
GROUP_ID = 243089386
ADMIN_ID = 200005093141 # Твой ID

vk_session = vk_api.VkApi(token=TOKEN)
longpoll = VkBotLongPoll(vk_session, GROUP_ID)
vk = vk_session.get_api()

# Хранилище данных в памяти (работает моментально)
balances = {}
active_chats = set()
promocodes = {} # Формат: {"КОД": сумма}

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

def get_activate_kb():
    return json.dumps({
        "inline": True,
        "buttons": [
            [{"action": {"type": "callback", "label": "🎮 Активировать", "payload": json.dumps({"cmd": "activate"})}, "color": "positive"}]
        ]
    }, ensure_ascii=False)

print("БОТ ЗАПУЩЕН (НОВЫЕ КОМАНДЫ)!")

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
                text = msg.get('text', '').strip()
                text_lower = text.lower()
                
                is_chat = peer_id > 2000000000

                if is_chat and peer_id not in active_chats:
                    continue

                balance = get_balance(user_id)
                parts = text_lower.split()

                # Ожидание ставки
                if user_id in waiting_for_bet:
                    game_data = waiting_for_bet[user_id]
                    game_type = game_data["game"]
                    choice = game_data.get("choice", None)
                    
                    if text_lower in ["отмена", "назад"]:
                        del waiting_for_bet[user_id]
                        send_msg(peer_id, "Ставка отменена.", reply_to=msg_id)
                        continue
                        
                    try:
                        if text_lower in ["всё", "все", "all"]:
                            bet_amount = balance
                        else:
                            bet_amount = int(text_lower)
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

                # --- НОВЫЕ КОМАНДЫ (С СУММОЙ В ОДНОЙ СТРОКЕ) ---

                elif text_lower.startswith("/красное"):
                    if len(parts) == 2 and parts[1].isdigit():
                        bet = int(parts[1])
                        waiting_for_bet[user_id] = {"game": "color", "choice": "red", "bet": bet}
                        send_msg(peer_id, f"🔴 Ты поставил {bet} на Красное. Крутим...", reply_to=msg_id)
                        # Дублируем логику игры для мгновенного ответа
                        if bet > balance or bet < 10:
                            del waiting_for_bet[user_id]
                            send_msg(peer_id, f"❌ Неверная ставка или нет денег (Баланс: {balance}).", reply_to=msg_id)
                        else:
                            del waiting_for_bet[user_id]
                            result_num = random.randint(0, 36)
                            is_red = result_num in [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]
                            if is_red:
                                set_balance(user_id, balance + bet)
                                send_msg(peer_id, f"🎉 ПОБЕДА! Выпало {result_num} 🔴. Ты выиграл {bet}!", reply_to=msg_id)
                            else:
                                set_balance(user_id, balance - bet)
                                send_msg(peer_id, f"😔 ПРОИГРЫШ. Выпало {result_num}. Ты потерял {bet}.", reply_to=msg_id)
                    else:
                        waiting_for_bet[user_id] = {"game": "color", "choice": "red"}
                        send_msg(peer_id, "🔴 Выбрано Красное. Напиши сумму ставки:", reply_to=msg_id)

                elif text_lower.startswith("/черное"):
                    if len(parts) == 2 and parts[1].isdigit():
                        bet = int(parts[1])
                        if bet > balance or bet < 10:
                            send_msg(peer_id, f"❌ Неверная ставка или нет денег (Баланс: {balance}).", reply_to=msg_id)
                        else:
                            result_num = random.randint(0, 36)
                            is_black = (result_num != 0) and (result_num not in [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36])
                            if is_black:
                                set_balance(user_id, balance + bet)
                                send_msg(peer_id, f"🎉 ПОБЕДА! Выпало {result_num} ⚫. Ты выиграл {bet}!", reply_to=msg_id)
                            else:
                                set_balance(user_id, balance - bet)
                                send_msg(peer_id, f"😔 ПРОИГРЫШ. Выпало {result_num}. Ты потерял {bet}.", reply_to=msg_id)
                    else:
                        waiting_for_bet[user_id] = {"game": "color", "choice": "black"}
                        send_msg(peer_id, "⚫ Выбрано Черное. Напиши сумму ставки:", reply_to=msg_id)

                elif text_lower.startswith("/чет"):
                    if len(parts) == 2 and parts[1].isdigit():
                        bet = int(parts[1])
                        if bet > balance or bet < 10:
                            send_msg(peer_id, f"❌ Неверная ставка или нет денег.", reply_to=msg_id)
                        else:
                            result_num = random.randint(0, 36)
                            if result_num != 0 and result_num % 2 == 0:
                                set_balance(user_id, balance + bet)
                                send_msg(peer_id, f"🎉 ПОБЕДА! Выпало {result_num}. Ты выиграл {bet}!", reply_to=msg_id)
                            else:
                                set_balance(user_id, balance - bet)
                                send_msg(peer_id, f"😔 ПРОИГРЫШ. Выпало {result_num}. Ты потерял {bet}.", reply_to=msg_id)
                    else:
                        waiting_for_bet[user_id] = {"game": "parity", "choice": "even"}
                        send_msg(peer_id, "🟢 Выбран Чет. Напиши сумму ставки:", reply_to=msg_id)

                elif text_lower.startswith("/нечет"):
                    if len(parts) == 2 and parts[1].isdigit():
                        bet = int(parts[1])
                        if bet > balance or bet < 10:
                            send_msg(peer_id, f"❌ Неверная ставка или нет денег.", reply_to=msg_id)
                        else:
                            result_num = random.randint(0, 36)
                            if result_num != 0 and result_num % 2 != 0:
                                set_balance(user_id, balance + bet)
                                send_msg(peer_id, f"🎉 ПОБЕДА! Выпало {result_num}. Ты выиграл {bet}!", reply_to=msg_id)
                            else:
                                set_balance(user_id, balance - bet)
                                send_msg(peer_id, f"😔 ПРОИГРЫШ. Выпало {result_num}. Ты потерял {bet}.", reply_to=msg_id)
                    else:
                        waiting_for_bet[user_id] = {"game": "parity", "choice": "odd"}
                        send_msg(peer_id, "🔴 Выбран Нечет. Напиши сумму ставки:", reply_to=msg_id)

                elif text_lower.startswith("/дрим"):
                    if len(parts) == 3 and parts[1].isdigit() and parts[2].isdigit():
                        num_choice = int(parts[1])
                        bet = int(parts[2])
                        if 1 <= num_choice <= 15 and bet >= 10 and bet <= balance:
                            result_num = random.randint(1, 15)
                            if result_num == num_choice:
                                set_balance(user_id, balance + bet * 10)
                                send_msg(peer_id, f"🔥 ДЖЕКПОТ! Выпало {result_num}. Ты выиграл x10: +{bet * 10}!", reply_to=msg_id)
                            else:
                                set_balance(user_id, balance - bet)
                                send_msg(peer_id, f"😔 ПРОИГРЫШ. Выпало {result_num}. Ты потерял {bet}.", reply_to=msg_id)
                        else:
                            send_msg(peer_id, "❌ Ошибка: число от 1 до 15, ставка от 10 и не больше баланса.", reply_to=msg_id)
                    else:
                        send_msg(peer_id, "❌ Напиши: /дрим [1-15] [сумма]. Пример: /дрим 7 500", reply_to=msg_id)

                elif text_lower.startswith("/rps"):
                    if len(parts) == 3 and parts[1] in ["камень", "ножницы", "бумага"] and parts[2].isdigit():
                        choice = parts[1]
                        bet = int(parts[2])
                        if bet >= 10 and bet <= balance:
                            bot_choice = random.choice(["камень", "ножницы", "бумага"])
                            win = False
                            draw = False
                            if choice == bot_choice: draw = True
                            elif (choice == "камень" and bot_choice == "ножницы") or \
                                 (choice == "ножницы" and bot_choice == "бумага") or \
                                 (choice == "бумага" and bot_choice == "камень"): win = True
                                 
                            if draw:
                                send_msg(peer_id, f"🤝 НИЧЬЯ!\nТы: {choice}\nБот: {bot_choice}", reply_to=msg_id)
                            elif win:
                                set_balance(user_id, balance + bet)
                                send_msg(peer_id, f"🎉 ПОБЕДА!\nТы: {choice}\nБот: {bot_choice}\nТы выиграл {bet}!", reply_to=msg_id)
                            else:
                                set_balance(user_id, balance - bet)
                                send_msg(peer_id, f"😔 ПРОИГРЫШ.\nТы: {choice}\nБот: {bot_choice}\nТы потерял {bet}.", reply_to=msg_id)
                        else:
                            send_msg(peer_id, "❌ Неверная ставка.", reply_to=msg_id)
                    else:
                        send_msg(peer_id, "❌ Напиши: /rps [камень/ножницы/бумага] [сумма]. Пример: /rps камень 500", reply_to=msg_id)

                # --- СЕКРЕТНАЯ КОМАНДА ДЛЯ СОЗДАНИЯ ПРОМОКОДА ---
                elif text_lower.startswith("/создать промокод"):
                    if user_id != ADMIN_ID:
                        send_msg(peer_id, "❌ У вас нет прав на эту команду.", reply_to=msg_id)
                        continue
                    
                    if len(parts) == 4 and parts[3].isdigit():
                        code_name = parts[2].upper()
                        amount = int(parts[3])
                        promocodes[code_name] = amount
                        send_msg(peer_id, f"✅ Промокод `{code_name}` на {amount} монет создан!", reply_to=msg_id)
                    else:
                        send_msg(peer_id, "❌ Напиши: /создать промокод [название] [сумма]", reply_to=msg_id)

                # --- АКТИВАЦИЯ ПРОМОКОДА ИГРОКОМ ---
                elif text_lower.startswith("/активировать"):
                    if len(parts) == 2:
                        code_name = parts[1].upper()
                        if code_name in promocodes:
                            amount = promocodes.pop(code_name) # Удаляем после использования
                            set_balance(user_id, balance + amount)
                            send_msg(peer_id, f"🎁 Промокод активирован! Ты получил {amount} монет.", reply_to=msg_id)
                        else:
                            send_msg(peer_id, "❌ Такого промокода не существует или он уже использован.", reply_to=msg_id)
                    else:
                        send_msg(peer_id, "❌ Напиши: /активировать [название]", reply_to=msg_id)

                # --- СТАРЫЕ КОМАНДЫ ---
                elif text_lower == "/help" or text_lower == "помощь":
                    help_text = ("📖 Команды:\n\n"
                                 "🎰 /казино\n"
                                 "🔴 /красное [сумма]\n"
                                 "⚫ /черное [сумма]\n"
                                 "🟢 /чет [сумма]\n"
                                 "🔴 /нечет [сумма]\n"
                                 "🔢 /дрим [1-15] [сумма]\n"
                                 "✂️ /rps [камень/ножницы/бумага] [сумма]\n"
                                 "🎁 /активировать [код]\n\n"
                                 "👤 /профиль\n"
                                 "🏆 /топ")
                    send_msg(peer_id, help_text, reply_to=msg_id)
                
                elif text_lower in ["начать", "start", "меню"]:
                    send_msg(peer_id, "🎰 Твой баланс: " + str(balance) + " монет.\nВведи /help.", reply_to=msg_id)
                
                elif text_lower == "/казино":
                    send_msg(peer_id, "🎰 Игры:\n/красное [сумма]\n/черное [сумма]\n/чет [сумма]\n/нечет [сумма]\n/дрим [1-15] [сумма]\n/rps [камень/ножницы/бумага] [сумма]", reply_to=msg_id)
                
                elif "профиль" in text_lower or "/профиль" in text_lower:
                    send_msg(peer_id, f"👤 Профиль:\n💰 Баланс: {balance} монет", reply_to=msg_id)
                
                elif "топ" in text_lower or "/топ" in text_lower:
                    # Сортируем игроков по балансу
                    sorted_players = sorted(balances.items(), key=lambda x: x[1], reverse=True)[:5]
                    top_text = "🏆 Топ 5 богачей:\n\n"
                    if not sorted_players:
                        top_text += "Пока никого нет."
                    else:
                        for i, (u, b) in enumerate(sorted_players, 1):
                            top_text += f"{i}. [id{u}|Игрок] — {b} монет\n"
                    send_msg(peer_id, top_text, reply_to=msg_id)
                
                else:
                    send_msg(peer_id, "Спасибо, что выбрали именно наш бот!\nВведите /help", reply_to=msg_id)

    except Exception as e:
        print(f"⚠️ Ошибка: {e}")
        time.sleep(2)
