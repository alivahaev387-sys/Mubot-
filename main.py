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

# База в памяти (не будет падать, но балансы сбросятся при перезапуске)
balances = {}
promocodes = {}

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

print("БОТ ЗАПУЩЕН (БЕЗ БАЗЫ)!")

while True:
    try:
        for event in longpoll.listen():
            
            # 1. Приглашение в беседу
            if event.type == VkBotEventType.MESSAGE_NEW and event.object.message.get('action'):
                action = event.object.message['action']
                if action.get('type') == 'chat_invite_user' and action.get('member_id') == -GROUP_ID:
                    peer_id = event.object.message['peer_id']
                    cm_id = event.object.message.get('conversation_message_id')
                    send_msg(peer_id, "Привет! Я игровой бот.\nНапиши /help, чтобы увидеть команды.", reply_to=cm_id)
                    continue

            # 2. Текстовые сообщения
            if event.type == VkBotEventType.MESSAGE_NEW and event.object.message.get('text'):
                msg = event.object.message
                peer_id = msg['peer_id']
                user_id = msg['from_id'] 
                cm_id = msg.get('conversation_message_id')
                
                text = msg.get('text', '').strip()
                text_lower = text.lower()
                parts = text_lower.split()

                balance = get_balance(user_id)
                is_ls = (peer_id == user_id)

                # --- ИГРЫ ---
                if text_lower.startswith("/красное"):
                    if len(parts) == 2 and parts[1].isdigit():
                        bet = int(parts[1])
                        if bet > balance or bet < 10:
                            send_msg(peer_id, f"❌ Ошибка: мин. ставка 10, баланс {balance}.", reply_to=cm_id)
                        else:
                            res = random.randint(0, 36)
                            if res in [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]:
                                set_balance(user_id, balance + bet)
                                send_msg(peer_id, f"🎉 ПОБЕДА! Выпало {res} 🔴. Ты выиграл {bet}!", reply_to=cm_id)
                            else:
                                set_balance(user_id, balance - bet)
                                send_msg(peer_id, f"😔 ПРОИГРЫШ. Выпало {res}. Ты потерял {bet}.", reply_to=cm_id)
                    else:
                        send_msg(peer_id, "❌ Напиши: /красное [сумма].", reply_to=cm_id)

                elif text_lower.startswith("/черное"):
                    if len(parts) == 2 and parts[1].isdigit():
                        bet = int(parts[1])
                        if bet > balance or bet < 10:
                            send_msg(peer_id, f"❌ Ошибка: мин. ставка 10, баланс {balance}.", reply_to=cm_id)
                        else:
                            res = random.randint(0, 36)
                            if res != 0 and res not in [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]:
                                set_balance(user_id, balance + bet)
                                send_msg(peer_id, f"🎉 ПОБЕДА! Выпало {res} ⚫. Ты выиграл {bet}!", reply_to=cm_id)
                            else:
                                set_balance(user_id, balance - bet)
                                send_msg(peer_id, f"😔 ПРОИГРЫШ. Выпало {res}. Ты потерял {bet}.", reply_to=cm_id)
                    else:
                        send_msg(peer_id, "❌ Напиши: /черное [сумма].", reply_to=cm_id)

                elif text_lower.startswith("/чет"):
                    if len(parts) == 2 and parts[1].isdigit():
                        bet = int(parts[1])
                        if bet > balance or bet < 10:
                            send_msg(peer_id, f"❌ Ошибка: мин. ставка 10, баланс {balance}.", reply_to=cm_id)
                        else:
                            res = random.randint(0, 36)
                            if res != 0 and res % 2 == 0:
                                set_balance(user_id, balance + bet)
                                send_msg(peer_id, f"🎉 ПОБЕДА! Выпало {res}. Ты выиграл {bet}!", reply_to=cm_id)
                            else:
                                set_balance(user_id, balance - bet)
                                send_msg(peer_id, f"😔 ПРОИГРЫШ. Выпало {res}. Ты потерял {bet}.", reply_to=cm_id)
                    else:
                        send_msg(peer_id, "❌ Напиши: /чет [сумма].", reply_to=cm_id)

                elif text_lower.startswith("/нечет"):
                    if len(parts) == 2 and parts[1].isdigit():
                        bet = int(parts[1])
                        if bet > balance or bet < 10:
                            send_msg(peer_id, f"❌ Ошибка: мин. ставка 10, баланс {balance}.", reply_to=cm_id)
                        else:
                            res = random.randint(0, 36)
                            if res != 0 and res % 2 != 0:
                                set_balance(user_id, balance + bet)
                                send_msg(peer_id, f"🎉 ПОБЕДА! Выпало {res}. Ты выиграл {bet}!", reply_to=cm_id)
                            else:
                                set_balance(user_id, balance - bet)
                                send_msg(peer_id, f"😔 ПРОИГРЫШ. Выпало {res}. Ты потерял {bet}.", reply_to=cm_id)
                    else:
                        send_msg(peer_id, "❌ Напиши: /нечет [сумма].", reply_to=cm_id)

                elif text_lower.startswith("/дрим"):
                    if len(parts) == 3 and parts[1].isdigit() and parts[2].isdigit():
                        num = int(parts[1])
                        bet = int(parts[2])
                        if 1 <= num <= 15 and bet >= 10 and bet <= balance:
                            res = random.randint(1, 15)
                            if res == num:
                                set_balance(user_id, balance + bet * 10)
                                send_msg(peer_id, f"🔥 ДЖЕКПОТ! Выпало {res}. Ты выиграл x10: +{bet * 10}!", reply_to=cm_id)
                            else:
                                set_balance(user_id, balance - bet)
                                send_msg(peer_id, f"😔 ПРОИГРЫШ. Выпало {res}. Ты потерял {bet}.", reply_to=cm_id)
                        else:
                            send_msg(peer_id, "❌ Ошибка: число от 1 до 15, ставка от 10.", reply_to=cm_id)
                    else:
                        send_msg(peer_id, "❌ Напиши: /дрим [1-15] [сумма].", reply_to=cm_id)

                elif text_lower.startswith("/rps"):
                    if len(parts) == 3 and parts[1] in ["камень", "ножницы", "бумага"] and parts[2].isdigit():
                        choice = parts[1]
                        bet = int(parts[2])
                        if bet >= 10 and bet <= balance:
                            bot = random.choice(["камень", "ножницы", "бумага"])
                            if choice == bot:
                                send_msg(peer_id, f"🤝 НИЧЬЯ!\nТы: {choice}\nБот: {bot}", reply_to=cm_id)
                            elif (choice == "камень" and bot == "ножницы") or (choice == "ножницы" and bot == "бумага") or (choice == "бумага" and bot == "камень"):
                                set_balance(user_id, balance + bet)
                                send_msg(peer_id, f"🎉 ПОБЕДА!\nТы: {choice}\nБот: {bot}\nТы выиграл {bet}!", reply_to=cm_id)
                            else:
                                set_balance(user_id, balance - bet)
                                send_msg(peer_id, f"😔 ПРОИГРЫШ.\nТы: {choice}\nБот: {bot}\nТы потерял {bet}.", reply_to=cm_id)
                        else:
                            send_msg(peer_id, "❌ Неверная ставка.", reply_to=cm_id)
                    else:
                        send_msg(peer_id, "❌ Напиши: /rps [камень/ножницы/бумага] [сумма].", reply_to=cm_id)

                # --- ПРОМОКОДЫ ---
                elif text_lower.startswith("/создать промокод"):
                    if user_id != ADMIN_ID:
                        send_msg(peer_id, "❌ Нет прав.", reply_to=cm_id)
                        continue
                    if len(parts) == 4 and parts[3].isdigit():
                        promocodes[parts[2].upper()] = int(parts[3])
                        send_msg(peer_id, f"✅ Промокод {parts[2].upper()} на {parts[3]} монет создан!", reply_to=cm_id)
                    else:
                        send_msg(peer_id, "❌ Напиши: /создать промокод [название] [сумма]", reply_to=cm_id)

                elif text_lower.startswith("/promo"):
                    if len(parts) == 2:
                        name = parts[1].upper()
                        if name in promocodes:
                            amount = promocodes.pop(name)
                            set_balance(user_id, balance + amount)
                            send_msg(peer_id, f"🎁 Промокод {name} активирован! +{amount} монет.", reply_to=cm_id)
                        else:
                            send_msg(peer_id, "❌ Неверное название или промокод уже использован.", reply_to=cm_id)
                    else:
                        send_msg(peer_id, "❌ Напиши: /promo [название]", reply_to=cm_id)

                # --- ОСТАЛЬНОЕ ---
                elif text_lower == "/help":
                    help_text = ("📖 Команды:\n\n"
                                 "🔴 /красное [сумма]\n"
                                 "⚫ /черное [сумма]\n"
                                 "🟢 /чет [сумма]\n"
                                 "🔴 /нечет [сумма]\n"
                                 "🔢 /дрим [1-15] [сумма]\n"
                                 "✂️ /rps [камень/ножницы/бумага] [сумма]\n"
                                 "🎁 /promo [название]\n\n"
                                 "👤 /профиль\n"
                                 "🏆 /топ")
                    if user_id == ADMIN_ID:
                        help_text += "\n\n👑 Для админа:\n/создать промокод [название] [сумма]"
                    send_msg(peer_id, help_text, reply_to=cm_id)
                
                elif text_lower in ["начать", "start", "меню"]:
                    if is_ls:
                        send_msg(peer_id, "🎰 Спасибо, что выбрали именно наш бот!\nВведи /help, чтобы увидеть команды.", reply_to=cm_id)
                
                elif "профиль" in text_lower or "/профиль" in text_lower:
                    send_msg(peer_id, f"👤 Профиль:\n💰 Баланс: {balance} монет", reply_to=cm_id)
                
                elif "топ" in text_lower or "/топ" in text_lower:
                    sorted_players = sorted(balances.items(), key=lambda x: x[1], reverse=True)[:5]
                    top_text = "🏆 Топ 5 богачей:\n\n"
                    if not sorted_players: top_text += "Пока никого нет."
                    else:
                        for i, (u, b) in enumerate(sorted_players, 1):
                            top_text += f"{i}. [id{u}|Игрок] — {b} монет\n"
                    send_msg(peer_id, top_text, reply_to=cm_id)
                
                # Всё остальное бот игнорирует

    except Exception as e:
        print(f"⚠️ Ошибка: {e}")
        time.sleep(2)
