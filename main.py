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

balances = {}
promocodes = {}
active_chats = set()

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

print("БОТ ЗАПУЩЕН (ФИНАЛЬНЫЙ)!")

while True:
    try:
        for event in longpoll.listen():
            
            # Добавление в беседу
            if event.type == VkBotEventType.MESSAGE_NEW and event.object.message.get('action'):
                action = event.object.message['action']
                if action.get('type') == 'chat_invite_user' and action.get('member_id') == -GROUP_ID:
                    peer_id = event.object.message['peer_id']
                    send_msg(peer_id, "Привет! Я игровой бот.\nНажми на кнопку, чтобы включить игры.", get_activate_kb())
                    continue

            # Кнопка активации
            if event.type == VkBotEventType.MESSAGE_EVENT:
                payload = event.object.payload
                if payload.get("cmd") == "activate":
                    active_chats.add(event.object.peer_id)
                    vk.messages.sendMessageEventAnswer(event_id=event.object.event_id, user_id=event.object.user_id, peer_id=event.object.peer_id, event_data=json.dumps({"type": "show_snackbar", "text": "✅ Успешно!"}))
                    send_msg(event.object.peer_id, "✅ Бот активирован! Пиши /help.")
                continue

            # Текстовые сообщения
            if event.type == VkBotEventType.MESSAGE_NEW and event.object.message.get('text'):
                msg = event.object.message
                peer_id = msg['peer_id']
                user_id = msg['from_id'] 
                msg_id = msg.get('id')
                
                text = msg.get('text', '').strip()
                text_lower = text.lower()
                parts = text_lower.split()

                balance = get_balance(user_id)

                # Игры
                if text_lower.startswith("/красное"):
                    if len(parts) == 2 and parts[1].isdigit():
                        bet = int(parts[1])
                        if bet > balance or bet < 10:
                            send_msg(peer_id, f"❌ Ошибка: мин. ставка 10, баланс {balance}.", reply_to=msg_id)
                        else:
                            res = random.randint(0, 36)
                            if res in [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]:
                                set_balance(user_id, balance + bet)
                                send_msg(peer_id, f"🎉 ПОБЕДА! Выпало {res} 🔴. Ты выиграл {bet}!", reply_to=msg_id)
                            else:
                                set_balance(user_id, balance - bet)
                                send_msg(peer_id, f"😔 ПРОИГРЫШ. Выпало {res}. Ты потерял {bet}.", reply_to=msg_id)
                    else:
                        send_msg(peer_id, "❌ Напиши: /красное [сумма].", reply_to=msg_id)

                elif text_lower.startswith("/черное"):
                    if len(parts) == 2 and parts[1].isdigit():
                        bet = int(parts[1])
                        if bet > balance or bet < 10:
                            send_msg(peer_id, f"❌ Ошибка: мин. ставка 10, баланс {balance}.", reply_to=msg_id)
                        else:
                            res = random.randint(0, 36)
                            if res != 0 and res not in [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]:
                                set_balance(user_id, balance + bet)
                                send_msg(peer_id, f"🎉 ПОБЕДА! Выпало {res} ⚫. Ты выиграл {bet}!", reply_to=msg_id)
                            else:
                                set_balance(user_id, balance - bet)
                                send_msg(peer_id, f"😔 ПРОИГРЫШ. Выпало {res}. Ты потерял {bet}.", reply_to=msg_id)
                    else:
                        send_msg(peer_id, "❌ Напиши: /черное [сумма].", reply_to=msg_id)

                elif text_lower.startswith("/чет"):
                    if len(parts) == 2 and parts[1].isdigit():
                        bet = int(parts[1])
                        if bet > balance or bet < 10:
                            send_msg(peer_id, f"❌ Ошибка: мин. ставка 10, баланс {balance}.", reply_to=msg_id)
                        else:
                            res = random.randint(0, 36)
                            if res != 0 and res % 2 == 0:
                                set_balance(user_id, balance + bet)
                                send_msg(peer_id, f"🎉 ПОБЕДА! Выпало {res}. Ты выиграл {bet}!", reply_to=msg_id)
                            else:
                                set_balance(user_id, balance - bet)
                                send_msg(peer_id, f"😔 ПРОИГРЫШ. Выпало {res}. Ты потерял {bet}.", reply_to=msg_id)
                    else:
                        send_msg(peer_id, "❌ Напиши: /чет [сумма].", reply_to=msg_id)

                elif text_lower.startswith("/нечет"):
                    if len(parts) == 2 and parts[1].isdigit():
                        bet = int(parts[1])
                        if bet > balance or bet < 10:
                            send_msg(peer_id, f"❌ Ошибка: мин. ставка 10, баланс {balance}.", reply_to=msg_id)
                        else:
                            res = random.randint(0, 36)
                            if res != 0 and res % 2 != 0:
                                set_balance(user_id, balance + bet)
                                send_msg(peer_id, f"🎉 ПОБЕДА! Выпало {res}. Ты выиграл {bet}!", reply_to=msg_id)
                            else:
                                set_balance(user_id, balance - bet)
                                send_msg(peer_id, f"😔 ПРОИГРЫШ. Выпало {res}. Ты потерял {bet}.", reply_to=msg_id)
                    else:
                        send_msg(peer_id, "❌ Напиши: /нечет [сумма].", reply_to=msg_id)

                elif text_lower.startswith("/дрим"):
                    if len(parts) == 3 and parts[1].isdigit() and parts[2].isdigit():
                        num = int(parts[1])
                        bet = int(parts[2])
                        if 1 <= num <= 15 and bet >= 10 and bet <= balance:
                            res = random.randint(1, 15)
                            if res == num:
                                set_balance(user_id, balance + bet * 10)
                                send_msg(peer_id, f"🔥 ДЖЕКПОТ! Выпало {res}. Ты выиграл x10: +{bet * 10}!", reply_to=msg_id)
                            else:
                                set_balance(user_id, balance - bet)
                                send_msg(peer_id, f"😔 ПРОИГРЫШ. Выпало {res}. Ты потерял {bet}.", reply_to=msg_id)
                        else:
                            send_msg(peer_id, "❌ Ошибка: число от 1 до 15, ставка от 10.", reply_to=msg_id)
                    else:
                        send_msg(peer_id, "❌ Напиши: /дрим [1-15] [сумма].", reply_to=msg_id)

                elif text_lower.startswith("/rps"):
                    if len(parts) == 3 and parts[1] in ["камень", "ножницы", "бумага"] and parts[2].isdigit():
                        choice = parts[1]
                        bet = int(parts[2])
                        if bet >= 10 and bet <= balance:
                            bot = random.choice(["камень", "ножницы", "бумага"])
                            if choice == bot:
                                send_msg(peer_id, f"🤝 НИЧЬЯ!\nТы: {choice}\nБот: {bot}", reply_to=msg_id)
                            elif (choice == "камень" and bot == "ножницы") or (choice == "ножницы" and bot == "бумага") or (choice == "бумага" and bot == "камень"):
                                set_balance(user_id, balance + bet)
                                send_msg(peer_id, f"🎉 ПОБЕДА!\nТы: {choice}\nБот: {bot}\nТы выиграл {bet}!", reply_to=msg_id)
                            else:
                                set_balance(user_id, balance - bet)
                                send_msg(peer_id, f"😔 ПРОИГРЫШ.\nТы: {choice}\nБот: {bot}\nТы потерял {bet}.", reply_to=msg_id)
                        else:
                            send_msg(peer_id, "❌ Неверная ставка.", reply_to=msg_id)
                    else:
                        send_msg(peer_id, "❌ Напиши: /rps [камень/ножницы/бумага] [сумма].", reply_to=msg_id)

                # Промокоды
                elif text_lower.startswith("/создать промокод"):
                    if user_id != ADMIN_ID:
                        send_msg(peer_id, "❌ Нет прав.", reply_to=msg_id)
                        continue
                    if len(parts) == 4 and parts[3].isdigit():
                        promocodes[parts[2].upper()] = int(parts[3])
                        send_msg(peer_id, f"✅ Промокод {parts[2].upper()} на {parts[3]} монет создан!", reply_to=msg_id)
                    else:
                        send_msg(peer_id, "❌ Напиши: /создать промокод [название] [сумма]", reply_to=msg_id)

                elif text_lower.startswith("/promo"):
                    if len(parts) == 2:
                        code = parts[1].upper()
                        
                        # ПРОВЕРКА НА ПОДПИСКУ
                        try:
                            member = vk.groups.isMember(group_id=GROUP_ID, user_id=user_id)
                            if member != 1:
                                send_msg(peer_id, "❌ Вы должны быть подписаны на сообщество, чтобы активировать промокод!", reply_to=msg_id)
                                continue
                        except Exception as e:
                            print(f"Ошибка проверки подписки: {e}")
                            send_msg(peer_id, "⚠️ Не удалось проверить подписку. Попробуйте позже.", reply_to=msg_id)
                            continue

                        if code in promocodes:
                            amount = promocodes.pop(code)
                            set_balance(user_id, balance + amount)
                            send_msg(peer_id, f"🎁 Промокод активирован! +{amount} монет.", reply_to=msg_id)
                        else:
                            send_msg(peer_id, "❌ Неверный или использованный промокод.", reply_to=msg_id)
                    else:
                        send_msg(peer_id, "❌ Напиши: /promo [название]", reply_to=msg_id)

                # Остальное
                elif text_lower == "/help":
                    help_text = ("📖 Команды:\n\n"
                                 "🔴 /красное [сумма]\n"
                                 "⚫ /черное [сумма]\n"
                                 "🟢 /чет [сумма]\n"
                                 "🔴 /нечет [сумма]\n"
                                 "🔢 /дрим [1-15] [сумма]\n"
                                 "✂️ /rps [камень/ножницы/бумага] [сумма]\n"
                                 "🎁 /promo [код]\n\n"
                                 "👤 /профиль\n"
                                 "🏆 /топ")
                    send_msg(peer_id, help_text, reply_to=msg_id)
                
                elif text_lower in ["начать", "start", "меню"]:
                    send_msg(peer_id, "🎰 Твой баланс: " + str(balance) + " монет.\nВведи /help.", reply_to=msg_id)
                
                elif "профиль" in text_lower or "/профиль" in text_lower:
                    send_msg(peer_id, f"👤 Профиль:\n💰 Баланс: {balance} монет", reply_to=msg_id)
                
                elif "топ" in text_lower or "/топ" in text_lower:
                    sorted_players = sorted(balances.items(), key=lambda x: x[1], reverse=True)[:5]
                    top_text = "🏆 Топ 5 богачей:\n\n"
                    if not sorted_players: top_text += "Пока никого нет."
                    else:
                        for i, (u, b) in enumerate(sorted_players, 1):
                            top_text += f"{i}. [id{u}|Игрок] — {b} монет\n"
                    send_msg(peer_id, top_text, reply_to=msg_id)
                
                # БОЛЬШЕ НЕТ ДЕФОЛТНОГО ОТВЕТА (просто игнорируем)

    except Exception as e:
        print(f"⚠️ Ошибка: {e}")
        time.sleep(2)
