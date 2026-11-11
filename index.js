const { VK, Keyboard } = require('vk-io');
const sqlite3 = require('sqlite3').verbose();
const fs = require('fs');
const path = require('path');

// ===== ПРОВЕРКА ВЕРСИИ =====
console.log("=========================================");
console.log("ВЕРСИЯ NODE.JS:", process.version);
console.log("=========================================");

// ===== НАСТРОЙКИ (ТВОЙ НОВЫЙ ТОКЕН) =====
const TOKEN = "vk1.a.BvMZnZvhxLsOu5bIQ1IUIIoYMEW3T88NqEAcRZ17Yj-T46O-viFXkUPWky-4XBwNZAKsWhcwqAt3TDMqQmcKva0ckucYDEUvFKa_p_LJ9ig-zNIPv7cHSZV9KP4S8XLgO0m32YWDLuqfz-rqgrrhoFKZ0mexTvf71NQ5G1JVI0H7QtuL4HGdtQkAvT7Up8xnC-vaO3QTue9x8V5a3u1-DuwMwEXIvfB4OgnVo0_FXGI";
const ADMIN_ID = 200005093141;
const BONUS_CD = 600; // 10 минут

const vk = new VK({ token: TOKEN, apiVersion: '5.131' });

const DATA_DIR = './data';
if (!fs.existsSync(DATA_DIR)) fs.mkdirSync(DATA_DIR);
const DB_FILE = path.join(DATA_DIR, 'game.db');

// ===== БАЗА ДАННЫХ =====
const db = new sqlite3.Database(DB_FILE);
const dbRun = (query, params = []) => new Promise((res, rej) => db.run(query, params, function(e) { e ? rej(e) : res(this); }));
const dbGet = (query, params = []) => new Promise((res, rej) => db.get(query, params, (e, r) => e ? rej(e) : res(r)));
const dbAll = (query, params = []) => new Promise((res, rej) => db.all(query, params, (e, r) => e ? rej(e) : res(r)));

async function initDB() {
    await dbRun("CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, balance INTEGER DEFAULT 1000)");
    await dbRun("CREATE TABLE IF NOT EXISTS active_duels (msg_id TEXT PRIMARY KEY, challenger TEXT, bet INTEGER, peer_id TEXT)");
    await dbRun("CREATE TABLE IF NOT EXISTS bonus_cd (user_id TEXT PRIMARY KEY, last_used INTEGER)");
    await dbRun("CREATE TABLE IF NOT EXISTS promos (code TEXT PRIMARY KEY, amount INTEGER, limit_count INTEGER, used_by TEXT DEFAULT '')");
    console.log("--- БАЗА ДАННЫХ ГОТОВА ---");
}
initDB();

// ===== ХЕЛПЕРЫ =====
async function getBalance(userId) {
    const row = await dbGet("SELECT balance FROM users WHERE user_id = ?", [String(userId)]);
    if (!row) {
        await dbRun("INSERT INTO users (user_id, balance) VALUES (?, 1000)", [String(userId)]);
        return 1000;
    }
    return row.balance;
}

async function updateBalance(userId, amount) {
    const bal = await getBalance(userId);
    await dbRun("UPDATE users SET balance = ? WHERE user_id = ?", [bal + amount, String(userId)]);
}

async function getName(userId) {
    try {
        const [user] = await vk.api.users.get({ user_ids: userId });
        return `[id${userId}|${user.first_name}]`;
    } catch { return `[id${userId}|Игрок]`; }
}

function formatMoney(num) { return num.toLocaleString('ru-RU'); }

// ===== КЛАВИАТУРЫ =====
const mainKb = Keyboard.builder()
    .textButton({ label: '💼 Работа', payload: 'work', color: Keyboard.POSITIVE_COLOR })
    .textButton({ label: '🎰 Рулетка', payload: 'roulette', color: Keyboard.PRIMARY_COLOR })
    .row()
    .textButton({ label: '👤 Профиль', payload: 'profile', color: Keyboard.SECONDARY_COLOR })
    .textButton({ label: '🏆 Топ', payload: 'top', color: Keyboard.SECONDARY_COLOR });

const getDuelKb = (duelId) => Keyboard.builder().inline().callbackButton({
    label: '⚔️ Сразиться',
    payload: { cmd: 'duel_accept', duel_id: duelId },
    color: Keyboard.POSITIVE_COLOR
});

// ===== ОБРАБОТКА СООБЩЕНИЙ =====
vk.updates.on('message_new', async (message) => {
    // Если сообщение от самого бота - пропускаем
    if (message.isOutbox) return;

    try {
        const text = message.text ? message.text.trim().toLowerCase() : '';
        if (!text) return;

        // ЛОГ: сообщение дошло до бота
        console.log(`\n[ПОЛУЧЕНО] Чат: ${message.peerId} | От: ${message.senderId} | Текст: ${text}`);

        const cleanText = text.replace(/\//g, '');
        const parts = cleanText.split(/\s+/);
        const userId = message.senderId;
        const peerId = message.peerId;
        const isLs = peerId === userId;

        const balance = await getBalance(userId);

        // --- КОМАНДЫ ---

        if (['help', 'помощь', 'команды'].includes(cleanText)) {
            const helpText = "📖 Команды:\n💼 Работа\n🎰 /рулетка [цвет/чет] [ставка]\n⚔️ /duel [сумма]\n🎁 /бонус\n🎁 /promo [код]\n📜 /промолист\n👤 /профиль\n🏆 /топ";
            return await message.reply(helpText, { keyboard: isLs ? mainKb : undefined });
        }

        if (text === '💼 работа' || text === 'работа') {
            const earned = Math.floor(Math.random() * 400) + 100;
            await updateBalance(userId, earned);
            const newBal = await getBalance(userId);
            return await message.reply(`✅ Ты заработал ${earned}$!\n💰 Баланс: ${formatMoney(newBal)}$`, { keyboard: isLs ? mainKb : undefined });
        }

        if (['профиль', 'баланс'].includes(cleanText)) {
            return await message.reply(`👤 Профиль:\n💰 Баланс: ${formatMoney(balance)}$\n🆔 ID: ${userId}`, { keyboard: isLs ? mainKb : undefined });
        }

        if (cleanText === 'топ') {
            const rows = await dbAll("SELECT user_id, balance FROM users WHERE balance > 2 ORDER BY balance DESC LIMIT 10");
            let topText = "🏆 Топ 10:\n\n";
            if (rows.length === 0) topText += "Пока пусто.";
            else {
                for (let i = 0; i < rows.length; i++) {
                    const uName = await getName(rows[i].user_id);
                    topText += `${i + 1}. ${uName} — ${formatMoney(rows[i].balance)}$\n`;
                }
            }
            return await message.reply(topText, { keyboard: isLs ? mainKb : undefined });
        }

        if (cleanText.startsWith('рулетка') || cleanText.startsWith('рул')) {
            if (parts.length >= 3) {
                const choice = parts[1];
                const betStr = parts[parts.length - 1];
                let bet = ['вб', 'всё', 'все'].includes(betStr) ? balance : parseInt(betStr);

                if (isNaN(bet) || bet < 10 || bet > balance) return await message.reply(`❌ Мин. ставка 10, у тебя ${formatMoney(balance)}$`);

                const res = Math.floor(Math.random() * 37);
                const redNumbers = [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36];
                
                let cName = redNumbers.includes(res) ? "Красное" : (res === 0 ? "Зеро" : "Черное");
                let cEmoji = redNumbers.includes(res) ? "🔴" : (res === 0 ? "🟢" : "⚫");
                let eName = res === 0 ? "Ноль" : (res % 2 === 0 ? "Четное" : "Нечетное");

                let win = (parseInt(choice) === res) || 
                          (["красное", "красный", "кр"].includes(choice) && redNumbers.includes(res)) ||
                          (["черное", "черный", "чр"].includes(choice) && !redNumbers.includes(res) && res !== 0) ||
                          (["чет", "четное"].includes(choice) && res % 2 === 0 && res !== 0) ||
                          (["нечет", "нечетное"].includes(choice) && res % 2 !== 0);

                if (win) {
                    await updateBalance(userId, bet);
                    return await message.reply(`🎰 Выпало: ${res} ${cEmoji} (${cName}, ${eName})\n\n✅ Выигрыш: +${bet}$\n💰 Баланс: ${formatMoney(await getBalance(userId))}$`, { keyboard: isLs ? mainKb : undefined });
                } else {
                    await updateBalance(userId, -bet);
                    return await message.reply(`🎰 Выпало: ${res} ${cEmoji} (${cName}, ${eName})\n\n😔 Проигрыш: -${bet}$\n💰 Баланс: ${formatMoney(await getBalance(userId))}$`, { keyboard: isLs ? mainKb : undefined });
                }
            } else {
                return await message.reply("❌ Формат: /рулетка красное 500");
            }
        }

        if (cleanText.startsWith('duel')) {
            if (parts.length === 2 && !isNaN(parts[1])) {
                const bet = parseInt(parts[1]);
                if (bet < 50 || bet > 2000) return await message.reply("❌ Ставка от 50 до 2000.");
                if (balance < bet) return await message.reply("❌ Не хватает монет.");

                const duelId = String(Math.floor(Math.random() * 90000) + 10000);
                await dbRun("REPLACE INTO active_duels (msg_id, challenger, bet, peer_id) VALUES (?, ?, ?, ?)", [duelId, String(userId), bet, String(peerId)]);

                return await message.reply(`⚔️ Дуэль!\n👤 Создатель: ${await getName(userId)}\n💰 Ставка: ${bet}$\n\n⚡ Нажми кнопку ниже!`, { keyboard: getDuelKb(duelId) });
            } else {
                return await message.reply("❌ Формат: /duel [сумма]");
            }
        }

        if (cleanText === 'бонус') {
            const currentTime = Math.floor(Date.now() / 1000);
            const row = await dbGet("SELECT last_used FROM bonus_cd WHERE user_id = ?", [String(userId)]);
            const lastUse = row ? row.last_used : 0;

            if (currentTime - lastUse < BONUS_CD) {
                const remaining = BONUS_CD - (currentTime - lastUse);
                return await message.reply(`⏳ Бонус доступен через ${Math.floor(remaining / 60)} мин. ${remaining % 60} сек.`);
            }

            const bonusAmount = [100000, 200000, 500000][Math.floor(Math.random() * 3)];
            await updateBalance(userId, bonusAmount);
            await dbRun("REPLACE INTO bonus_cd (user_id, last_used) VALUES (?, ?)", [String(userId), currentTime]);
            
            return await message.reply(`🎁 Бонус получен! ✨\n+${formatMoney(bonusAmount)}$\n💰 Баланс: ${formatMoney(await getBalance(userId))}$`, { keyboard: isLs ? mainKb : undefined });
        }

        if (userId === ADMIN_ID) {
            if (cleanText.startsWith('деньги')) {
                if (parts.length === 2 && !isNaN(parts[1]) && message.hasReplyMessage) {
                    const amount = parseInt(parts[1]);
                    const targetId = message.replyMessage.senderId;
                    await updateBalance(targetId, amount);
                    return await message.reply(`💰 Владелец выдал ${formatMoney(amount)}$ игроку ${await getName(targetId)}!`);
                } else {
                    return await message.reply("❌ Формат: /деньги [сумма] (ответом на сообщение)");
                }
            }

            if (cleanText.startsWith('создать')) {
                if (parts.length === 4 && !isNaN(parts[2]) && !isNaN(parts[3])) {
                    await dbRun("REPLACE INTO promos (code, amount, limit_count, used_by) VALUES (?, ?, ?, '')", [parts[1], parseInt(parts[2]), parseInt(parts[3])]);
                    return await message.reply(`✅ Промокод \`${parts[1]}\` создан!`);
                } else {
                    return await message.reply("❌ Формат: /создать [код] [сумма] [лимит]");
                }
            }
        }

        if (cleanText === 'промолист') {
            const rows = await dbAll("SELECT code, amount, limit_count, used_by FROM promos");
            if (rows.length === 0) return await message.reply("❌ Активных промокодов нет.");
            
            let promoList = "🎁 Активные промокоды:\n\n";
            for (const r of rows) {
                const usedCount = r.used_by ? r.used_by.split(",").length : 0;
                promoList += `▪️ \`${r.code}\` — ${r.amount}$ (${usedCount}/${r.limit_count})\n`;
            }
            return await message.reply(promoList);
        }

        if (cleanText.startsWith('promo')) {
            if (parts.length === 2) {
                const row = await dbGet("SELECT amount, limit_count, used_by FROM promos WHERE code = ?", [parts[1]]);
                
                if (!row) return await message.reply("❌ Промокод не существует или исчерпан.");
                
                const usedBy = row.used_by ? row.used_by.split(",") : [];
                if (usedBy.length >= row.limit_count) {
                    await dbRun("DELETE FROM promos WHERE code = ?", [parts[1]]);
                    return await message.reply("❌ Промокод больше не действителен.");
                }
                
                if (usedBy.includes(String(userId))) return await message.reply("❌ Ты уже активировал этот промокод!");
                
                usedBy.push(String(userId));
                await updateBalance(userId, row.amount);
                
                if (usedBy.length >= row.limit_count) {
                    await dbRun("DELETE FROM promos WHERE code = ?", [parts[1]]);
                    return await message.reply(`✅ Активирован! +${row.amount}$\n⚠️ Промокод удален (лимит исчерпан).`);
                } else {
                    await dbRun("UPDATE promos SET used_by = ? WHERE code = ?", [usedBy.join(","), parts[1]]);
                    return await message.reply(`✅ Активирован! +${row.amount}$\nОсталось: ${row.limit_count - usedBy.length}`);
                }
            } else {
                return await message.reply("❌ Формат: /promo [код]");
            }
        }

    } catch (error) {
        console.error("КРИТИЧЕСКАЯ ОШИБКА ПРИ ОБРАБОТКЕ:", error);
        try {
            await message.reply(`⚠️ Ошибка на стороне бота:\n${error.message}`);
        } catch (e) {}
    }
});

// ===== ОБРАБОТКА КНОПОК =====
vk.updates.on('message_event', async (context) => {
    try {
        const payload = context.eventPayload;
        if (payload.cmd === 'duel_accept') {
            const duelId = payload.duel_id;
            const row = await dbGet("SELECT challenger, bet FROM active_duels WHERE msg_id = ?", [duelId]);
            
            if (row) {
                if (String(context.userId) === row.challenger) return await context.answer({ type: 'show_snackbar', text: '❌ Нельзя драться с собой!' });
                if (await getBalance(context.userId) < row.bet) return await context.answer({ type: 'show_snackbar', text: '❌ Не хватает денег!' });
                
                const winnerId = Math.random() < 0.5 ? parseInt(row.challenger) : context.userId;
                const loserId = winnerId === context.userId ? parseInt(row.challenger) : context.userId;
                const prize = Math.floor(row.bet * 1.8);
                
                await updateBalance(winnerId, prize);
                await updateBalance(loserId, -row.bet);
                await dbRun("DELETE FROM active_duels WHERE msg_id = ?", [duelId]);
                
                const msgText = `⚔️ Дуэль завершена!\n\n🏆 Победитель: ${await getName(winnerId)}\n❌ Проигравший: ${await getName(loserId)}\n\n💰 Выигрыш: ${prize}$`;
                
                await context.editMessage({ message: msgText, keyboard: null });
                return await context.answer({ type: 'show_snackbar', text: '⚔️ Дуэль завершена!' });
            }
        }
    } catch (e) {
        console.error("Ошибка в кнопках:", e);
    }
});

// ===== ЗАПУСК =====
console.log("ПОПЫТКА ЗАПУСКА БОТА...");
vk.updates.startPolling().then(() => {
    console.log("--- БОТ УСПЕШНО ЗАПУЩЕН (LONGPOLL) ---");
}).catch(err => {
    console.error("ОШИБКА ПРИ СТАРТЕ:", err);
});
