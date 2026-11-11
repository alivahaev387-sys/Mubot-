const { VK, Keyboard } = require('vk-io');
const sqlite3 = require('sqlite3').verbose();
const fs = require('fs');
const path = require('path');

// ===== НАСТРОЙКИ =====
const TOKEN = "vk1.a.n-y1VnQMFI87cAGH7zXHwYy6LncLM_UuAaCihe6dlWxUBLGwS8no-KjRmFrA9zmwy-STfP7f2VZOHArq1-WVKYVRUA3H1F3-pO5gtXRxEziw3u3st-dTYHNiK_an2ZcbUIpXYNy98HHTGQv12wFtMLsSASQ0kO0ke0B0DRsXc7hn-LQrYcpbu54a_kQmP7dxBO5a8gTmuS9Dn9LH7oMLfE6G6_GPJZxJAgkwzptCnWw";
const ADMIN_ID = 200005093141;
const BONUS_CD = 600; // 10 минут

// Инициализация VK
const vk = new VK({ token: TOKEN, apiVersion: '5.131' });

// Создаем папку для БД, если ее нет
const DATA_DIR = './data';
if (!fs.existsSync(DATA_DIR)) fs.mkdirSync(DATA_DIR);
const DB_FILE = path.join(DATA_DIR, 'game.db');

// ===== БАЗА ДАННЫХ =====
const db = new sqlite3.Database(DB_FILE);

// Обертки для асинхронной работы с БД
const dbRun = (query, params = []) => new Promise((resolve, reject) => {
    db.run(query, params, function (err) { if (err) reject(err); else resolve(this); });
});
const dbGet = (query, params = []) => new Promise((resolve, reject) => {
    db.get(query, params, (err, row) => { if (err) reject(err); else resolve(row); });
});
const dbAll = (query, params = []) => new Promise((resolve, reject) => {
    db.all(query, params, (err, rows) => { if (err) reject(err); else resolve(rows); });
});

// Инициализация таблиц
async function initDB() {
    await dbRun("CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, balance INTEGER DEFAULT 1000)");
    await dbRun("CREATE TABLE IF NOT EXISTS active_duels (msg_id TEXT PRIMARY KEY, challenger TEXT, bet INTEGER, peer_id TEXT)");
    await dbRun("CREATE TABLE IF NOT EXISTS bonus_cd (user_id TEXT PRIMARY KEY, last_used INTEGER)");
    await dbRun("CREATE TABLE IF NOT EXISTS promos (code TEXT PRIMARY KEY, amount INTEGER, limit_count INTEGER, used_by TEXT DEFAULT '')");
    console.log("--- БОТ ЗАПУЩЕН УСПЕШНО ---");
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
    } catch {
        return `[id${userId}|Игрок]`;
    }
}

function formatMoney(num) {
    return num.toLocaleString('ru-RU');
}

// ===== КЛАВИАТУРЫ =====
const mainKb = Keyboard.builder()
    .textButton({ label: '💼 Работа', payload: 'work', color: Keyboard.POSITIVE_COLOR })
    .textButton({ label: '🎰 Рулетка', payload: 'roulette', color: Keyboard.PRIMARY_COLOR })
    .row()
    .textButton({ label: '👤 Профиль', payload: 'profile', color: Keyboard.SECONDARY_COLOR })
    .textButton({ label: '🏆 Топ', payload: 'top', color: Keyboard.SECONDARY_COLOR });

const getDuelKb = (duelId) => Keyboard.builder()
    .inline()
    .callbackButton({
        label: '⚔️ Сразиться',
        payload: { cmd: 'duel_accept', duel_id: duelId },
        color: Keyboard.POSITIVE_COLOR
    });

// ===== ОБРАБОТКА СООБЩЕНИЙ (ТЕКСТ) =====
vk.updates.on('message_new', async (context) => {
    if (context.isOutbox) return;

    const text = context.text ? context.text.trim().toLowerCase() : '';
    const cleanText = text.replace(/\//g, '');
    const parts = cleanText.split(/\s+/);
    const userId = context.senderId;
    const peerId = context.peerId;
    const isLs = peerId === userId;

    if (!text) return;

    const balance = await getBalance(userId);

    // 1. ПОМОЩЬ
    if (['help', 'помощь', 'команды'].includes(cleanText)) {
        const helpText = 
            "📖 Доступные команды:\n\n" +
            "💼 Работа — Заработать деньги\n" +
            "🎰 /рулетка [цвет/чет] [ставка] — Игра\n" +
            "⚔️ /duel [сумма] — Дуэль\n" +
            "🎁 /бонус — Бонус (раз в 10 минут)\n" +
            "🎁 /promo [код] — Активировать промокод\n" +
            "📜 /промолист — Список активных промокодов\n" +
            "👤 /профиль — Твой баланс\n" +
            "🏆 /топ — Топ богачей";
        // Используем context.reply() — он сам делает реплай!
        return context.reply(helpText, { keyboard: isLs ? mainKb : undefined });
    }

    // 2. РАБОТА
    if (text === '💼 работа') {
        const earned = Math.floor(Math.random() * 400) + 100; // 100-500
        await updateBalance(userId, earned);
        const newBal = await getBalance(userId);
        return context.reply(`✅ Ты заработал ${earned}$!\n💰 Баланс: ${formatMoney(newBal)}$`, { keyboard: mainKb });
    }

    // 3. ПРОФИЛЬ
    if (['профиль', 'баланс'].includes(cleanText)) {
        return context.reply(`👤 Твой профиль:\n💰 Баланс: ${formatMoney(balance)}$\n🆔 ID: ${userId}`, { keyboard: isLs ? mainKb : undefined });
    }

    // 4. ТОП
    if (cleanText === 'топ') {
        const rows = await dbAll("SELECT user_id, balance FROM users WHERE balance > 2 ORDER BY balance DESC LIMIT 10");
        let topText = "🏆 Топ 10 богачей:\n\n";
        if (rows.length === 0) {
            topText += "Пока пусто.";
        } else {
            for (let i = 0; i < rows.length; i++) {
                const uName = await getName(rows[i].user_id);
                topText += `${i + 1}. ${uName} — ${formatMoney(rows[i].balance)}$\n`;
            }
        }
        return context.reply(topText, { keyboard: isLs ? mainKb : undefined });
    }

    // 5. РУЛЕТКА
    if (cleanText.startsWith('рулетка') || cleanText.startsWith('рул')) {
        if (parts.length >= 3) {
            const choice = parts[1];
            const betStr = parts[parts.length - 1];
            let bet = 0;

            if (['вб', 'всё', 'все'].includes(betStr)) bet = balance;
            else if (!isNaN(betStr)) bet = parseInt(betStr);
            else return context.reply("❌ Неверная ставка.");

            if (bet < 10 || bet > balance) return context.reply(`❌ Мин. ставка 10, у тебя ${formatMoney(balance)}$`);

            const res = Math.floor(Math.random() * 37); // 0-36
            const redNumbers = [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36];
            
            let colorName = "", colorEmoji = "", evenName = "";
            if (redNumbers.includes(res)) { colorName = "Красное"; colorEmoji = "🔴"; }
            else if (res === 0) { colorName = "Зеро"; colorEmoji = "🟢"; }
            else { colorName = "Черное"; colorEmoji = "⚫"; }

            if (res === 0) evenName = "Ноль";
            else if (res % 2 === 0) evenName = "Четное";
            else evenName = "Нечетное";

            let win = false;
            if (!isNaN(choice) && parseInt(choice) === res) win = true;
            else if (["красное", "красный", "кр"].includes(choice) && redNumbers.includes(res)) win = true;
            else if (["черное", "черный", "чр"].includes(choice) && !redNumbers.includes(res) && res !== 0) win = true;
            else if (["чет", "четное"].includes(choice) && res % 2 === 0 && res !== 0) win = true;
            else if (["нечет", "нечетное"].includes(choice) && res % 2 !== 0) win = true;

            let msgText = "";
            if (win) {
                await updateBalance(userId, bet);
                msgText = `🎰 Выпало: ${res} ${colorEmoji} (${colorName}, ${evenName})\n\n✅ Ты выиграл: +${bet}$\n💰 Баланс: ${formatMoney(await getBalance(userId))}$`;
            } else {
                await updateBalance(userId, -bet);
                msgText = `🎰 Выпало: ${res} ${colorEmoji} (${colorName}, ${evenName})\n\n😔 Ты проиграл: -${bet}$\n💰 Баланс: ${formatMoney(await getBalance(userId))}$`;
            }
            return context.reply(msgText, { keyboard: isLs ? mainKb : undefined });
        } else {
            return context.reply("❌ Формат: /рулетка красное 500");
        }
    }

    // 6. ДУЭЛИ
    if (cleanText.startsWith('duel')) {
        if (parts.length === 2 && !isNaN(parts[1])) {
            const bet = parseInt(parts[1]);
            if (bet < 50 || bet > 2000) return context.reply("❌ Ставка от 50 до 2000.");
            if (balance < bet) return context.reply("❌ Не хватает монет.");

            const duelId = String(Math.floor(Math.random() * 90000) + 10000);
            await dbRun("REPLACE INTO active_duels (msg_id, challenger, bet, peer_id) VALUES (?, ?, ?, ?)", [duelId, String(userId), bet, String(peerId)]);

            const duelText = 
                `⚔️ Дуэль!\n👤 Создатель: ${await getName(userId)}\n` +
                `💰 Ставка: ${bet}$\n\n🌑 Приз: ${Math.floor(bet * 1.8)}$\n⚡ Нажми кнопку ниже!`;
            
            return context.reply(duelText, { keyboard: getDuelKb(duelId) });
        } else {
            return context.reply("❌ Формат: /duel [сумма] (от 50 до 2000)");
        }
    }

    // 7. БОНУС
    if (cleanText === 'бонус') {
        const currentTime = Math.floor(Date.now() / 1000);
        const row = await dbGet("SELECT last_used FROM bonus_cd WHERE user_id = ?", [String(userId)]);
        const lastUse = row ? row.last_used : 0;

        if (currentTime - lastUse < BONUS_CD) {
            const remaining = BONUS_CD - (currentTime - lastUse);
            return context.reply(`⏳ Бонус доступен через ${Math.floor(remaining / 60)} мин. ${remaining % 60} сек.`);
        }

        const bonusAmount = [100000, 200000, 500000][Math.floor(Math.random() * 3)];
        await updateBalance(userId, bonusAmount);
        await dbRun("REPLACE INTO bonus_cd (user_id, last_used) VALUES (?, ?)", [String(userId), currentTime]);
        
        const newBal = await getBalance(userId);
        return context.reply(`🎁 Бонус получен! ✨\n+${formatMoney(bonusAmount)}$\n💰 Баланс: ${formatMoney(newBal)}$`, { keyboard: isLs ? mainKb : undefined });
    }

    // ===== АДМИНСКИЕ КОМАНДЫ =====
    if (userId === ADMIN_ID) {
        // ВЫДАЧА ДЕНЕГ
        if (cleanText.startsWith('деньги')) {
            if (parts.length === 2 && !isNaN(parts[1]) && context.hasReplyMessage) {
                const amount = parseInt(parts[1]);
                const targetId = context.replyMessage.senderId;
                await updateBalance(targetId, amount);
                return context.reply(`💰 Владелец выдал ${formatMoney(amount)}$ игроку ${await getName(targetId)}!`);
            } else {
                return context.reply("❌ Формат: /деньги [сумма] (ответом на сообщение)");
            }
        }

        // СОЗДАНИЕ ПРОМОКОДА
        if (cleanText.startsWith('создать')) {
            if (parts.length === 4 && !isNaN(parts[2]) && !isNaN(parts[3])) {
                const code = parts[1];
                const amount = parseInt(parts[2]);
                const limit = parseInt(parts[3]);
                await dbRun("REPLACE INTO promos (code, amount, limit_count, used_by) VALUES (?, ?, ?, '')", [code, amount, limit]);
                return context.reply(`✅ Промокод \`${code}\` на ${amount}$ (Лимит: ${limit}) создан!`);
            } else {
                return context.reply("❌ Формат: /создать [код] [сумма] [лимит]");
            }
        }
    }

    // 8. СПИСОК ПРОМОКОДОВ
    if (cleanText === 'промолист') {
        const rows = await dbAll("SELECT code, amount, limit_count, used_by FROM promos");
        if (rows.length === 0) return context.reply("❌ Активных промокодов нет.");
        
        let promoList = "🎁 Активные промокоды:\n\n";
        for (const r of rows) {
            const usedCount = r.used_by ? r.used_by.split(",").length : 0;
            promoList += `▪️ \`${r.code}\` — ${r.amount}$ (Активировали: ${usedCount}/${r.limit_count})\n`;
        }
        return context.reply(promoList);
    }

    // 9. АКТИВАЦИЯ ПРОМОКОДА
    if (cleanText.startsWith('promo')) {
        if (parts.length === 2) {
            const code = parts[1];
            const row = await dbGet("SELECT amount, limit_count, used_by FROM promos WHERE code = ?", [code]);
            
            if (!row) return context.reply("❌ Промокод не существует или уже исчерпан.");
            
            const amount = row.amount;
            const limit = row.limit_count;
            const usedBy = row.used_by ? row.used_by.split(",") : [];
            
            if (usedBy.length >= limit) {
                await dbRun("DELETE FROM promos WHERE code = ?", [code]);
                return context.reply("❌ Промокод больше не действителен.");
            }
            
            if (usedBy.includes(String(userId))) return context.reply("❌ Ты уже активировал этот промокод!");
            
            usedBy.push(String(userId));
            await updateBalance(userId, amount);
            
            if (usedBy.length >= limit) {
                await dbRun("DELETE FROM promos WHERE code = ?", [code]);
                return context.reply(`✅ Промокод активирован! +${amount}$\n⚠️ Это была последняя активация. Промокод удален.`);
            } else {
                await dbRun("UPDATE promos SET used_by = ? WHERE code = ?", [usedBy.join(","), code]);
                return context.reply(`✅ Промокод активирован! +${amount}$\nОсталось активаций: ${limit - usedBy.length}`);
            }
        } else {
            return context.reply("❌ Формат: /promo [код]");
        }
    }
});

// ===== ОБРАБОТКА НАЖАТИЙ НА КНОПКИ (ДУЭЛИ) =====
vk.updates.on('message_event', async (context) => {
    const payload = context.eventPayload;

    if (payload.cmd === 'duel_accept') {
        const duelId = payload.duel_id;
        const userId = context.userId;
        
        const row = await dbGet("SELECT challenger, bet, peer_id FROM active_duels WHERE msg_id = ?", [duelId]);
        
        if (row) {
            const challenger = row.challenger;
            const bet = row.bet;
            
            if (String(userId) === challenger) {
                return context.answer({ type: 'show_snackbar', text: '❌ Нельзя драться с собой!' });
            }
            
            const userBalance = await getBalance(userId);
            if (userBalance < bet) {
                return context.answer({ type: 'show_snackbar', text: '❌ Не хватает денег!' });
            }
            
            // Рандомим победителя
            const winnerId = Math.random() < 0.5 ? parseInt(challenger) : userId;
            const loserId = winnerId === userId ? parseInt(challenger) : userId;
            const prize = Math.floor(bet * 1.8);
            
            await updateBalance(winnerId, prize);
            await updateBalance(loserId, -bet);
            
            await dbRun("DELETE FROM active_duels WHERE msg_id = ?", [duelId]);
            
            const winnerName = await getName(winnerId);
            const loserName = await getName(loserId);
            
            const msgText = 
                `⚔️ Дуэль завершена!\n\n` +
                `🏆 Победитель: ${winnerName}\n` +
                `❌ Проигравший: ${loserName}\n\n` +
                `💰 Выигрыш: ${prize}$`;
            
            // Редактируем сообщение (убираем inline-кнопку)
            await context.editMessage({ message: msgText, keyboard: null });
            
            return context.answer({ type: 'show_snackbar', text: '⚔️ Дуэль завершена!' });
        }
    }
});

// Запуск LongPoll
vk.updates.start().catch(console.error);
