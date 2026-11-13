const { VK, Keyboard } = require('vk-io');
const sqlite3 = require('sqlite3').verbose();
const fs = require('fs');
const path = require('path');

console.log("=========================================");
console.log("ВЕРСИЯ NODE.JS:", process.version);
console.log("=========================================");

// ===== НАСТРОЙКИ =====
const TOKEN = "vk1.a.K6H21Ezx3iiNIiHM5Xe8LiL_Uto5Q3UBixGMIdGETKmStwhfTmUmjad9K2YMVptEipNk0chqVadrmScyl5uISAYcI6IUfqaj8UlW25bo7ZwLxhQIsQ4sX6vJx8_wD1y2ZtJe-aaX4egzHx8YMFQ2gvObMiqfEUCS5PqYHPXXNigRJ6m0EAiatL6xWwjIJRaRTcPVo_hYGRad1TOz8anPJLzl4VJUem7AE3I_QwzYUVY";
const GROUP_ID = 243089386;
const ADMIN_ID = 200005093141;
const BONUS_CD = 600; 
const FORTUNA_CD = 600;

const vk = new VK({ 
    token: TOKEN, 
    apiVersion: '5.199',
    pollingGroupId: GROUP_ID 
});

const DATA_DIR = './data';
if (!fs.existsSync(DATA_DIR)) fs.mkdirSync(DATA_DIR);
const DB_FILE = path.join(DATA_DIR, 'game.db');

// ===== БАЗА ДАННЫХ =====
const db = new sqlite3.Database(DB_FILE);
const dbRun = (query, params = []) => new Promise((res, rej) => db.run(query, params, function(e) { e ? rej(e) : res(this); }));
const dbGet = (query, params = []) => new Promise((res, rej) => db.get(query, params, (e, r) => e ? rej(e) : res(r)));
const dbAll = (query, params = []) => new Promise((res, rej) => db.all(query, params, (e, r) => e ? rej(e) : res(r)));

// Данные бизнесов
const BIZ_DATA = {
    'шаурма': { name: '🌯 Шаурма', price: 500000, baseIncome: 1000 },
    'кафе': { name: '☕ Кафе', price: 1500000, baseIncome: 3000 },
    'game zone': { name: '🕹️ Отдел Game Zone', price: 5000000, baseIncome: 10000 },
    'казино': { name: '🎰 Казино', price: 15000000, baseIncome: 30000 },
    'пятерочка': { name: '🏪 24/7 Пятёрочка', price: 50000000, baseIncome: 100000 }
};

async function initDB() {
    await dbRun("CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, balance INTEGER DEFAULT 1000, reputation INTEGER DEFAULT 0, xp INTEGER DEFAULT 0, level INTEGER DEFAULT 1, reg_date TEXT)");
    await dbRun("CREATE TABLE IF NOT EXISTS active_duels (msg_id TEXT PRIMARY KEY, challenger TEXT, bet INTEGER, peer_id TEXT)");
    await dbRun("CREATE TABLE IF NOT EXISTS bonus_cd (user_id TEXT PRIMARY KEY, last_used INTEGER)");
    await dbRun("CREATE TABLE IF NOT EXISTS fortune_cd (user_id TEXT PRIMARY KEY, last_used INTEGER)");
    await dbRun("CREATE TABLE IF NOT EXISTS promos (code TEXT PRIMARY KEY, amount INTEGER, limit_count INTEGER, used_by TEXT DEFAULT '')");
    await dbRun("CREATE TABLE IF NOT EXISTS games (game_id TEXT PRIMARY KEY, user_id TEXT, bet INTEGER, mines TEXT, opened TEXT, multiplier REAL, msg_id TEXT)");
    await dbRun("CREATE TABLE IF NOT EXISTS blacklist (user_id TEXT PRIMARY KEY, reason TEXT)");
    await dbRun("CREATE TABLE IF NOT EXISTS chat_messages (peer_id TEXT, user_id TEXT, count INTEGER DEFAULT 0, PRIMARY KEY (peer_id, user_id))");
    await dbRun("CREATE TABLE IF NOT EXISTS businesses (user_id TEXT PRIMARY KEY, biz_name TEXT, level INTEGER DEFAULT 1, balance INTEGER DEFAULT 0, last_income INTEGER)");
    
    // Миграции для старых баз
    try { await dbRun("ALTER TABLE users ADD COLUMN reputation INTEGER DEFAULT 0"); } catch(e) {}
    try { await dbRun("ALTER TABLE users ADD COLUMN xp INTEGER DEFAULT 0"); } catch(e) {}
    try { await dbRun("ALTER TABLE users ADD COLUMN level INTEGER DEFAULT 1"); } catch(e) {}
    try { await dbRun("ALTER TABLE users ADD COLUMN reg_date TEXT"); } catch(e) {}
    
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
    return Number(row.balance) || 0; // Возвращаем строго число, чтобы не было NaN
}

async function updateBalance(userId, amount) {
    const bal = await getBalance(userId);
    const newBal = Math.floor(Number(bal) + Number(amount));
    await dbRun("UPDATE users SET balance = ? WHERE user_id = ?", [newBal, String(userId)]);
}

async function getReputation(userId) {
    const row = await dbGet("SELECT reputation FROM users WHERE user_id = ?", [String(userId)]);
    return row ? (Number(row.reputation) || 0) : 0;
}

async function updateReputation(userId, amount) {
    const rep = await getReputation(userId);
    await dbRun("UPDATE users SET reputation = ? WHERE user_id = ?", [rep + amount, String(userId)]);
}

async function getFullName(userId) {
    try {
        const [user] = await vk.api.users.get({ user_ids: userId });
        return `[id${userId}|${user.first_name} ${user.last_name || ''}]`;
    } catch { return `[id${userId}|Игрок]`; }
}

function formatMoney(num) { 
    let n = Number(num);
    if (isNaN(n) || !isFinite(n)) n = 0;
    return n.toLocaleString('ru-RU'); 
}

async function getTargetAndReason(message, cmdName) {
    let targetId = null;
    let text = message.text;
    let reason = text.replace(new RegExp(`^\\/?${cmdName}\\s*`, 'i'), '');

    if (message.hasReplyMessage) {
        targetId = message.replyMessage.senderId;
    } else {
        const idMatch = reason.match(/\[id(\d+)\|[^\]]+\]/i);
        if (idMatch) {
            targetId = parseInt(idMatch[1]);
            reason = reason.replace(idMatch[0], ''); 
        } else {
            const atIdMatch = reason.match(/@id(\d+)/i);
            if (atIdMatch) {
                targetId = parseInt(atIdMatch[1]);
                reason = reason.replace(atIdMatch[0], ''); 
            } else {
                const mentionMatch = reason.match(/@([a-zA-Z0-9._]+)/);
                if (mentionMatch) {
                    try {
                        const res = await vk.api.utils.resolveScreenName({ screen_name: mentionMatch[1] });
                        if (res.type === 'user') targetId = res.object_id;
                    } catch (e) {}
                    reason = reason.replace(mentionMatch[0], ''); 
                }
            }
        }
    }

    reason = reason.replace(/[\[\]]/g, '').replace(/"/g, '').trim();
    if (!reason) reason = "Причина не указана";

    return { targetId, reason };
}

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
}).toString();

const getMinesCountKb = (gameId) => {
    const kb = Keyboard.builder().inline();
    let count = 0;
    for (let i = 2; i <= 8; i++) {
        kb.callbackButton({ label: `${i} 💣`, payload: { cmd: 'mines_set', gameId: String(gameId), count: String(i) }, color: Keyboard.SECONDARY_COLOR });
        count++;
        if (count % 4 === 0 && i !== 8) kb.row();
    }
    return kb.toString();
};

const getMinesFieldKb = (gameId, opened, mines, isGameOver = false) => {
    const kb = Keyboard.builder().inline();
    for (let i = 1; i <= 9; i++) {
        if (opened.includes(i)) {
            kb.callbackButton({ label: mines.includes(i) ? '💥' : '💎', payload: { cmd: 'none' }, color: mines.includes(i) ? Keyboard.NEGATIVE_COLOR : Keyboard.POSITIVE_COLOR });
        } else {
            kb.callbackButton({ label: String(i), payload: isGameOver ? { cmd: 'none' } : { cmd: 'mines_click', gameId: String(gameId), cell: String(i) }, color: Keyboard.SECONDARY_COLOR });
        }
        if (i % 3 === 0) kb.row();
    }
    if (!isGameOver) kb.callbackButton({ label: '💰 Забрать', payload: { cmd: 'mines_cashout', gameId: String(gameId) }, color: Keyboard.POSITIVE_COLOR });
    return kb.toString();
};

// Динамическая клавиатура для Топов
const getTopKb = (authorId, type, scope, repType = 'pos') => {
    const kb = Keyboard.builder().inline();
    
    // Ряд 1: Выбор категории
    kb.callbackButton({ label: '💰 Монеты', payload: { cmd: 'top_menu', type: 'coins', scope: scope, author: authorId }, color: type === 'coins' ? Keyboard.PRIMARY_COLOR : Keyboard.SECONDARY_COLOR });
    kb.callbackButton({ label: '⭐ Репутация', payload: { cmd: 'top_menu', type: 'rep', scope: scope, repType: repType, author: authorId }, color: type === 'rep' ? Keyboard.PRIMARY_COLOR : Keyboard.SECONDARY_COLOR });
    kb.callbackButton({ label: '📊 Уровень', payload: { cmd: 'top_menu', type: 'level', scope: scope, author: authorId }, color: type === 'level' ? Keyboard.PRIMARY_COLOR : Keyboard.SECONDARY_COLOR });
    kb.row();

    // Ряд 2: Отрицательная репа (если выбрана репа)
    if (type === 'rep') {
        kb.callbackButton({ label: '➕ Положительные', payload: { cmd: 'top_menu', type: 'rep', scope: scope, repType: 'pos', author: authorId }, color: repType === 'pos' ? Keyboard.POSITIVE_COLOR : Keyboard.SECONDARY_COLOR });
        kb.callbackButton({ label: '➖ Отрицательные', payload: { cmd: 'top_menu', type: 'rep', scope: scope, repType: 'neg', author: authorId }, color: repType === 'neg' ? Keyboard.NEGATIVE_COLOR : Keyboard.SECONDARY_COLOR });
        kb.row();
    }

    // Ряд 3: Область (Общий / В беседе)
    kb.callbackButton({ label: '🌍 Общий', payload: { cmd: 'top_menu', type: type, scope: 'global', repType: repType, author: authorId }, color: scope === 'global' ? Keyboard.PRIMARY_COLOR : Keyboard.SECONDARY_COLOR });
    kb.callbackButton({ label: '💬 В беседе', payload: { cmd: 'top_menu', type: type, scope: 'chat', repType: repType, author: authorId }, color: scope === 'chat' ? Keyboard.PRIMARY_COLOR : Keyboard.SECONDARY_COLOR });

    return kb.toString();
};

const getBizKb = (authorId) => Keyboard.builder().inline()
    .callbackButton({ label: '💵 Вывести', payload: { cmd: 'biz_withdraw', author: authorId }, color: Keyboard.POSITIVE_COLOR })
    .row()
    .callbackButton({ label: '📈 Повысить уровень', payload: { cmd: 'biz_upgrade', author: authorId }, color: Keyboard.PRIMARY_COLOR })
    .row()
    .callbackButton({ label: '💀 Закрыть бизнес', payload: { cmd: 'biz_close', author: authorId }, color: Keyboard.NEGATIVE_COLOR })
    .toString();

// ===== ПРИВЕТСТВИЕ =====
vk.updates.on('chat_invite_user', async (context) => {
    if (String(context.memberId) === String(-GROUP_ID)) {
        const actKb = Keyboard.builder().inline()
            .callbackButton({ label: 'Активировать', payload: { cmd: 'activate_bot' }, color: Keyboard.POSITIVE_COLOR })
            .callbackButton({ label: 'Не активировать', payload: { cmd: 'decline_bot' }, color: Keyboard.NEGATIVE_COLOR });
        
        try {
            await vk.api.messages.send({
                peer_id: context.peerId,
                message: "Привет! Я Официальный бот Game Zone. Для того чтобы я начал работать, выдайте мне права администратора и напишите /start. После этого напишите /help для ознакомления с командами.",
                keyboard: actKb.toString(),
                random_id: Math.floor(Math.random() * 1000000000),
                group_id: GROUP_ID,
                disable_mentions: 1
            });
        } catch (err) {}
    }
});

// ===== ОБРАБОТКА СООБЩЕНИЙ =====
vk.updates.on('message_new', async (message) => {
    if (message.isOutbox) return;
    if (message.senderId < 0) return;

    try {
        const text = message.text ? message.text.trim().toLowerCase() : '';
        if (!text) return;

        const userId = message.senderId;
        const peerId = message.peerId;
        const isLs = peerId === userId;

        // --- СИСТЕМА УРОВНЕЙ (XP) ---
        let userRow = await dbGet("SELECT xp, level, reg_date FROM users WHERE user_id = ?", [String(userId)]);
        if (!userRow) {
            const today = new Date().toLocaleDateString('ru-RU');
            await dbRun("INSERT INTO users (user_id, balance, reg_date) VALUES (?, 1000, ?)", [String(userId), today]);
        } else {
            if (!userRow.reg_date) {
                const today = new Date().toLocaleDateString('ru-RU');
                await dbRun("UPDATE users SET reg_date = ? WHERE user_id = ?", [today, String(userId)]);
            }
            // Выдаем 40 XP за сообщение
            let newXp = (Number(userRow.xp) || 0) + 40;
            let newLvl = Number(userRow.level) || 1;
            while (newXp >= newLvl * 500) {
                newXp -= newLvl * 500;
                newLvl++;
            }
            await dbRun("UPDATE users SET xp = ?, level = ? WHERE user_id = ?", [newXp, newLvl, String(userId)]);
        }

        // Счетчик сообщений
        if (message.isChat) {
            const existing = await dbGet("SELECT count FROM chat_messages WHERE peer_id = ? AND user_id = ?", [String(peerId), String(userId)]);
            if (existing) {
                await dbRun("UPDATE chat_messages SET count = count + 1 WHERE peer_id = ? AND user_id = ?", [String(peerId), String(userId)]);
            } else {
                await dbRun("INSERT INTO chat_messages (peer_id, user_id, count) VALUES (?, ?, 1)", [String(peerId), String(userId)]);
            }
        }

        // Проверка на ЧС
        if (text.startsWith('/')) {
            const isBlacklisted = await dbGet("SELECT reason FROM blacklist WHERE user_id = ?", [String(userId)]);
            if (isBlacklisted) {
                return await message.reply(`🚫 Доступ запрещен!\n\n👤 Ваш ID: ${userId}\n📝 Вы в черном списке бота.\n📌 Причина: ${isBlacklisted.reason}`, { disable_mentions: 1 });
            }
        }

        if (!text.startsWith('/') && text !== '💼 работа') return;

        const cleanText = text.replace(/\//g, '').trim();
        const parts = cleanText.split(/\s+/);

        const balance = await getBalance(userId);
        const rep = await getReputation(userId);

        const replyParams = (kb = undefined) => {
            const p = { disable_mentions: 1 };
            if (kb) p.keyboard = kb;
            return p;
        };

        // --- КОМАНДА START (Только для админов) ---
        if (text.includes('начать') || text.includes('start')) {
            if (message.isChat) {
                try {
                    const members = await vk.api.messages.getConversationMembers({ peer_id: peerId });
                    const admin = members.items.find(m => m.member_id === userId && (m.is_admin || m.is_owner));
                    
                    if (!admin && userId !== ADMIN_ID) {
                        return await message.reply("⚠️ Ошибка! Вы не являетесь администратором беседы. Чтобы активировать бота, попросите администратора написать /start.", replyParams());
                    }
                    return await message.reply("✅ Бот успешно активирован в этой беседе! Напишите /help для списка команд.", replyParams());
                } catch(e) {
                    return await message.reply("⚠️ Ошибка! Убедитесь, что я являюсь администратором беседы.", replyParams());
                }
            } else {
                return await message.reply("👋 Привет! Я Официальный бот Game Zone. Выбирай действие на клавиатуре или напиши /help.", replyParams(mainKb));
            }
        }

        // --- HELP ---
        if (text.includes('help') || text.includes('помощь') || text.includes('команды')) {
            const helpText = "📖 Команды:\n🎰 /рулетка [цвет/чет] [ставка]\n🎲 /фортуна (100$)\n💣 /мины [ставка]\n⚔️ /duel [сумма]\n💸 /transfer [сумма] (ответом)\n🎁 /бонус\n🎁 /promo [код]\n📜 /промолист\n👤 /профиль\n🏆 /топ\n🏢 /бизнес\n🛒 /купитьбиз [название]\n💼 /мойбизнес\n👍 /rep +/- изменения репутации";
            return await message.reply(helpText, replyParams(isLs ? mainKb : undefined));
        }

        // --- ПРОФИЛЬ ---
        if (cleanText === 'профиль' || cleanText === 'баланс') {
            const uInfo = await dbGet("SELECT xp, level, reg_date FROM users WHERE user_id = ?", [String(userId)]);
            const lvl = uInfo.level || 1;
            const xp = uInfo.xp || 0;
            const needXp = lvl * 500;
            const date = uInfo.reg_date || new Date().toLocaleDateString('ru-RU');

            return await message.reply(`🏠 Профиль ${await getFullName(userId)}\n\n💵 Баланс: ${formatMoney(balance)}$\n⭐ Репутация: ${rep}\n📊 Уровень: ${lvl} (${xp}/${needXp} XP)\n📅 Дата регистрации: ${date}\n🆔 ID: ${userId}`, replyParams(isLs ? mainKb : undefined));
        }

        // --- ТОП (Главное меню) ---
        if (cleanText === 'топ' || cleanText === 'top') {
            const rows = await dbAll("SELECT user_id, count FROM chat_messages WHERE peer_id = ? ORDER BY count DESC LIMIT 10", [String(peerId)]);
            let topText = "⭐ ТОП 10 ПОЛЬЗОВАТЕЛЕЙ ПО СООБЩЕНИЯМ (В этой беседе)\n\n";
            
            if (rows.length > 0) {
                const userIds = rows.map(r => r.user_id);
                let usersInfo = [];
                try { usersInfo = await vk.api.users.get({ user_ids: userIds.join(','), fields: 'deactivated' }); } catch (e) {}
                let count = 0;
                const emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"];
                for (const r of rows) {
                    const uInfo = usersInfo.find(u => u.id == r.user_id);
                    if (uInfo && !uInfo.deactivated) {
                        topText += `${emojis[count]} [id${uInfo.id}|${uInfo.first_name} ${uInfo.last_name || ''}] - ${r.count} сообщений\n`;
                        count++;
                    }
                }
            } else {
                topText += "В этой беседе еще никто не писал.";
            }

            return await message.reply(topText, replyParams(getTopKb(userId, 'coins', 'chat')));
        }

        // --- БИЗНЕСЫ ---
        if (cleanText === 'бизнес') {
            let bizText = "🏢 Доступные бизнесы для покупки:\n\n";
            for (const [key, data] of Object.entries(BIZ_DATA)) {
                bizText += `${data.name} — ${formatMoney(data.price)}$ (Доход: ~${formatMoney(data.baseIncome)}$/3мин)\n`;
            }
            bizText += "\nЧтобы купить, напишите /купитьбиз [Название]\nПример: /купитьбиз Шаурма";
            return await message.reply(bizText, replyParams());
        }

        if (cleanText.startsWith('купитьбиз')) {
            const args = message.text.split(' ');
            args.shift(); // Убираем саму команду
            const bizQuery = args.join(' ').toLowerCase().trim();
            
            if (!bizQuery) return await message.reply("❌ Укажите, какой бизнес хотите купить. Пример: /купитьбиз Шаурма");

            const existing = await dbGet("SELECT biz_name FROM businesses WHERE user_id = ?", [String(userId)]);
            if (existing) return await message.reply("❌ У вас уже есть бизнес. Сначала закройте текущий (/мойбизнес).");

            let selectedBiz = null;
            for (const [key, data] of Object.entries(BIZ_DATA)) {
                if (key.includes(bizQuery) || data.name.toLowerCase().includes(bizQuery)) {
                    selectedBiz = data;
                    break;
                }
            }

            if (!selectedBiz) return await message.reply("❌ Такого бизнеса нет. Посмотрите список: /бизнес");
            if (balance < selectedBiz.price) return await message.reply(`❌ Не хватает денег! Нужно ${formatMoney(selectedBiz.price)}$`);

            await updateBalance(userId, -selectedBiz.price);
            await dbRun("INSERT INTO businesses (user_id, biz_name, level, balance, last_income) VALUES (?, ?, 1, 0, ?)", [String(userId), selectedBiz.name, Date.now()]);
            
            return await message.reply(`🎉 Поздравляем! Вы успешно купили ${selectedBiz.name} за ${formatMoney(selectedBiz.price)}$.\nУдачи в заработке! Пишите /мойбизнес для управления.`, replyParams());
        }

        if (cleanText === 'мойбизнес') {
            const biz = await dbGet("SELECT * FROM businesses WHERE user_id = ?", [String(userId)]);
            if (!biz) return await message.reply("❌ У вас нет бизнеса. Купите его: /бизнес");

            const bizData = Object.values(BIZ_DATA).find(b => b.name === biz.biz_name) || { name: biz.biz_name, baseIncome: 1000 };
            const timePassed = Date.now() - biz.last_income;
            const incomePerMs = (bizData.baseIncome * biz.level) / 180000; // Доход в час (каждые 3 мин = 180000 мс)
            const earned = Math.floor(timePassed * incomePerMs);
            const totalBalance = Number(biz.balance) + earned;
            const nextLevelCost = (Number(biz.level) === 1 ? 2000000 : Number(biz.level) === 2 ? 5000000 : Number(biz.level) * 5000000);

            const msgText = `🏢 Бизнес ${await getFullName(userId)}\n${biz.biz_name}\n\n💪 Уровень: ${biz.level}/5\n📈 Доход: ${formatMoney(bizData.baseIncome * biz.level)}$/3мин\n💵 На балансе бизнеса: ${formatMoney(totalBalance)}$\n\nПовышение уровня стоит: ${formatMoney(nextLevelCost)}$`;

            return await message.reply(msgText, replyParams(getBizKb(userId)));
        }

        // --- РЕПУТАЦИЯ ---
        if (text === '/rep' || text === 'реп') {
            return await message.reply("🔔 Для изменения репутации используйте /rep + или /rep -, указав пользователя. Пример: /rep + @Mokhma.volk", replyParams());
        }

        if (text.startsWith('/rep +') || text.startsWith('/rep -')) {
            const isPlus = text.startsWith('/rep +');
            let targetId = null;
            
            if (message.hasReplyMessage) {
                targetId = message.replyMessage.senderId;
            } else {
                const targetStr = text.replace('/rep +', '').replace('/rep -', '').trim();
                const mentionMatch = targetStr.match(/@([a-zA-Z0-9._]+)/) || targetStr.match(/\[id(\d+)\|/);
                if (mentionMatch) {
                    if(mentionMatch[1].match(/^\d+$/)) targetId = parseInt(mentionMatch[1]);
                    else {
                        try {
                            const res = await vk.api.utils.resolveScreenName({ screen_name: mentionMatch[1] });
                            if (res.type === 'user') targetId = res.object_id;
                        } catch (e) {}
                    }
                }
            }

            if (!targetId) return await message.reply("⚠️ Укажите пользователя через @упоминание или ответом на сообщение.", replyParams());
            if (targetId === userId) return await message.reply("❌ Вы не можете изменить репутацию самому себе!", replyParams());

            if (isPlus) {
                await updateReputation(targetId, 1);
                return await message.reply(`🟢 ${await getFullName(userId)} повысил репутацию пользователя ${await getFullName(targetId)} (Теперь у него ${await getReputation(targetId)})`, replyParams());
            } else {
                await updateReputation(targetId, -1);
                return await message.reply(`🔴 ${await getFullName(userId)} понизил репутацию пользователя ${await getFullName(targetId)} (Теперь у него ${await getReputation(targetId)})`, replyParams());
            }
        }

        // --- ИГРЫ (Остальное) ---
        if (text === '💼 работа') {
            const earned = Math.floor(Math.random() * 400) + 100;
            await updateBalance(userId, earned);
            return await message.reply(`✅ Ты заработал ${earned}$!\n💰 Баланс: ${formatMoney(await getBalance(userId))}$`, replyParams(isLs ? mainKb : undefined));
        }

        if (cleanText.startsWith('рулетка') || cleanText.startsWith('рул')) {
            if (parts.length >= 3) {
                const choice = parts[1];
                const betStr = parts[parts.length - 1];
                let bet = ['вб', 'всё', 'все'].includes(betStr) ? balance : parseInt(betStr);

                if (isNaN(bet) || bet < 10 || bet > balance) return await message.reply(`❌ Мин. ставка 10, у тебя ${formatMoney(balance)}$`, replyParams());

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
                    return await message.reply(`🎰 Выпало: ${res} ${cEmoji} (${cName}, ${eName})\n\n✅ Выигрыш: +${bet}$\n💰 Баланс: ${formatMoney(await getBalance(userId))}$`, replyParams(isLs ? mainKb : undefined));
                } else {
                    await updateBalance(userId, -bet);
                    return await message.reply(`🎰 Выпало: ${res} ${cEmoji} (${cName}, ${eName})\n\n😔 Проигрыш: -${bet}$\n💰 Баланс: ${formatMoney(await getBalance(userId))}$`, replyParams(isLs ? mainKb : undefined));
                }
            } else {
                return await message.reply("❌ Формат: /рулетка красное 500", replyParams());
            }
        }

        if (cleanText === 'фортуна') {
            const currentTime = Math.floor(Date.now() / 1000);
            const row = await dbGet("SELECT last_used FROM fortune_cd WHERE user_id = ?", [String(userId)]);
            const lastUse = row ? row.last_used : 0;

            if (currentTime - lastUse < FORTUNA_CD) {
                const remaining = FORTUNA_CD - (currentTime - lastUse);
                return await message.reply(`⏳ Фортуна доступна через ${Math.floor(remaining / 60)} мин. ${remaining % 60} сек.`, replyParams());
            }
            if (balance < 100) return await message.reply("❌ Фортуна стоит 100$.", replyParams());

            await updateBalance(userId, -100);
            await dbRun("REPLACE INTO fortune_cd (user_id, last_used) VALUES (?, ?)", [String(userId), currentTime]);

            const prize = [0, 50, 100, 200, 500, 1000, 5000][Math.floor(Math.random() * 7)];
            await updateBalance(userId, prize);
            
            return await message.reply(`🎰 Выпало: ${formatMoney(prize)}$!\n💰 Баланс: ${formatMoney(await getBalance(userId))}$`, replyParams(isLs ? mainKb : undefined));
        }

        if (cleanText.startsWith('мины')) {
            let bet = 100;
            if (parts.length >= 2) {
                if (['все', 'вб', 'всё'].includes(parts[1])) bet = balance;
                else if (!isNaN(parts[1])) bet = parseInt(parts[1]);
            }

            if (bet < 10 || bet > balance) return await message.reply(`❌ Мин. ставка 10, у тебя ${formatMoney(balance)}$`, replyParams());

            const gameId = String(Math.floor(Math.random() * 90000) + 10000);
            await dbRun("INSERT INTO games (game_id, user_id, bet, mines, opened, multiplier, msg_id) VALUES (?, ?, ?, '[]', '[]', 1.0, ?)", [gameId, String(userId), bet, String(message.id)]);

            return await message.reply(`💣 Мины\nСтавка: ${bet}$\n\nВыберите количество мин (2-8):`, replyParams(getMinesCountKb(gameId)));
        }

        if (cleanText.startsWith('transfer') || cleanText.startsWith('перевод')) {
            if (parts.length >= 2 && !isNaN(parts[1]) && message.hasReplyMessage) {
                const amount = parseInt(parts[1]);
                const targetId = message.replyMessage.senderId;

                if (targetId === userId) return await message.reply("❌ Нельзя перевести деньги самому себе.", replyParams());
                if (targetId < 0) return await message.reply("❌ Нельзя переводить сообществам.", replyParams());
                if (amount < 50 || amount > 5000000) return await message.reply("❌ Сумма перевода должна быть от 50 до 5 000 000$", replyParams());
                if (balance < amount) return await message.reply("❌ У тебя недостаточно средств.", replyParams());

                await updateBalance(userId, -amount);
                await updateBalance(targetId, amount);

                const targetName = await getFullName(targetId);
                return await message.reply(`💸 Ты успешно перевел ${formatMoney(amount)}$ игроку ${targetName}.\n💰 Твой баланс: ${formatMoney(await getBalance(userId))}$`, replyParams());
            } else {
                return await message.reply("❌ Формат: /transfer [сумма] (ответом на сообщение)", replyParams());
            }
        }

        if (cleanText.startsWith('duel')) {
            if (parts.length === 2 && !isNaN(parts[1])) {
                const bet = parseInt(parts[1]);
                if (bet < 50 || bet > 2000) return await message.reply("❌ Ставка от 50 до 2000.", replyParams());
                if (balance < bet) return await message.reply("❌ Не хватает монет.", replyParams());

                const duelId = String(Math.floor(Math.random() * 90000) + 10000);
                await dbRun("REPLACE INTO active_duels (msg_id, challenger, bet, peer_id) VALUES (?, ?, ?, ?)", [duelId, String(userId), bet, String(peerId)]);

                return await message.reply(`⚔️ Дуэль!\n👤 Создатель: ${await getFullName(userId)}\n💰 Ставка: ${bet}$\n\n⚡ Нажми кнопку ниже!`, replyParams(getDuelKb(duelId)));
            } else {
                return await message.reply("❌ Формат: /duel [сумма]", replyParams());
            }
        }

        if (cleanText === 'бонус') {
            const currentTime = Math.floor(Date.now() / 1000);
            const row = await dbGet("SELECT last_used FROM bonus_cd WHERE user_id = ?", [String(userId)]);
            const lastUse = row ? row.last_used : 0;

            if (currentTime - lastUse < BONUS_CD) {
                const remaining = BONUS_CD - (currentTime - lastUse);
                return await message.reply(`⏳ Бонус доступен через ${Math.floor(remaining / 60)} мин. ${remaining % 60} сек.`, replyParams());
            }

            const bonusAmount = [100000, 200000, 500000][Math.floor(Math.random() * 3)];
            await updateBalance(userId, bonusAmount);
            await dbRun("REPLACE INTO bonus_cd (user_id, last_used) VALUES (?, ?)", [String(userId), currentTime]);
            
            return await message.reply(`🎁 Бонус получен! ✨\n+${formatMoney(bonusAmount)}$\n💰 Баланс: ${formatMoney(await getBalance(userId))}$`, replyParams(isLs ? mainKb : undefined));
        }

        // ===== АДМИНСКИЕ КОМАНДЫ =====
        if (userId === ADMIN_ID) {
            if (cleanText.startsWith('kick')) {
                if (parts.length === 1 && !message.hasReplyMessage) {
                    return await message.reply("🔔 Чтобы исключить пользователя из чата, используйте /kick @VK Причина (Пример: /kick @andrey_mala Тест)", replyParams());
                }

                const { targetId, reason } = await getTargetAndReason(message, 'kick');

                if (!targetId) return await message.reply("⚠️ Указанный пользователь не является участником данной беседы, либо же имеет статус выше Вашего.", replyParams());
                if (targetId === ADMIN_ID) return await message.reply("❌ Вы не можете исключить самого себя.", replyParams());
                if (!message.isChat) return await message.reply("❌ Эту команду можно использовать только в беседе.", replyParams());

                const chatId = message.peerId - 2000000000;
                const targetName = await getFullName(targetId);
                const senderName = await getFullName(message.senderId);

                try {
                    await vk.api.messages.removeChatUser({ chat_id: chatId, user_id: targetId, group_id: GROUP_ID });
                    return await message.reply(`${senderName} исключил(-а) из беседы пользователя ${targetName} по причине: "${reason}"`, replyParams());
                } catch (e) {
                    return await message.reply(`⚠️ Указанный пользователь не является участником данной беседы, либо же имеет статус выше Вашего.`, replyParams());
                }
            }

            if (cleanText.startsWith('чсб')) {
                if (parts.length === 1 && !message.hasReplyMessage) {
                    return await message.reply("🔔 Чтобы занести в ЧС, используйте /чсб @VK Причина (Пример: /чсб @andrey_mala Спам)", replyParams());
                }

                const { targetId, reason } = await getTargetAndReason(message, 'чсб');

                if (!targetId) return await message.reply("⚠️ Указанный пользователь не является участником данной беседы, либо же имеет статус выше Вашего.", replyParams());
                if (targetId === ADMIN_ID) return await message.reply("❌ Вы не можете занести себя в ЧС.", replyParams());
                
                await dbRun("REPLACE INTO blacklist (user_id, reason) VALUES (?, ?)", [String(targetId), reason]);
                const targetName = await getFullName(targetId);
                const senderName = await getFullName(message.senderId);
                
                return await message.reply(`${senderName} занес(-ла) в ЧС бота пользователя ${targetName} по причине: "${reason}"`, replyParams());
            }

            if (cleanText.startsWith('разчсб')) {
                const { targetId } = await getTargetAndReason(message, 'разчсб');
                if (!targetId) return await message.reply("⚠️ Указанный пользователь не является участником данной беседы, либо же имеет статус выше Вашего.", replyParams());

                await dbRun("DELETE FROM blacklist WHERE user_id = ?", [String(targetId)]);
                const targetName = await getFullName(targetId);
                const senderName = await getFullName(message.senderId);
                
                return await message.reply(`${senderName} разбанил(-а) пользователя ${targetName} в ЧС бота.`, replyParams());
            }

            if (cleanText === 'cp') {
                await dbRun("DELETE FROM promos");
                return await message.reply("✅ Все активные промокоды были успешно удалены.", replyParams());
            }

            if (cleanText.startsWith('деньги')) {
                if (parts.length === 2 && !isNaN(parts[1]) && message.hasReplyMessage) {
                    const amount = Number(parts[1]); // Используем Number для огромных сумм
                    const targetId = message.replyMessage.senderId;
                    await updateBalance(targetId, amount);
                    return await message.reply(`💰 Владелец выдал ${formatMoney(amount)}$ игроку ${await getFullName(targetId)}!`, replyParams());
                } else {
                    return await message.reply("❌ Формат: /деньги [сумма] (ответом на сообщение)", replyParams());
                }
            }

            if (cleanText.startsWith('создать')) {
                if (parts.length === 4 && !isNaN(parts[2]) && !isNaN(parts[3])) {
                    await dbRun("REPLACE INTO promos (code, amount, limit_count, used_by) VALUES (?, ?, ?, '')", [parts[1], parseInt(parts[2]), parseInt(parts[3])]);
                    return await message.reply(`✅ Промокод \`${parts[1]}\` создан!`, replyParams());
                } else {
                    return await message.reply("❌ Формат: /создать [код] [сумма] [лимит]", replyParams());
                }
            }
        }

        if (cleanText === 'промолист') {
            const rows = await dbAll("SELECT code, amount, limit_count, used_by FROM promos");
            if (rows.length === 0) return await message.reply("❌ Активных промокодов нет.", replyParams());
            
            let promoList = "🎁 Активные промокоды:\n\n";
            for (const r of rows) {
                const usedCount = r.used_by ? r.used_by.split(",").length : 0;
                promoList += `▪️ \`${r.code}\` — ${r.amount}$ (${usedCount}/${r.limit_count})\n`;
            }
            return await message.reply(promoList, replyParams());
        }

        if (cleanText.startsWith('promo')) {
            if (parts.length === 2) {
                try {
                    const isMember = await vk.api.groups.isMember({ group_id: GROUP_ID, user_id: userId });
                    if (isMember !== 1) {
                        const subKb = Keyboard.builder().inline().urlButton({ label: '📢 Подписаться', url: `https://vk.com/public${GROUP_ID}` });
                        return await message.reply("⚠️ Промокоды доступны только подписчикам нашего сообщества!\n\nПодпишитесь на группу и попробуйте снова.", replyParams(subKb.toString()));
                    }
                } catch (e) {}

                const row = await dbGet("SELECT amount, limit_count, used_by FROM promos WHERE code = ?", [parts[1]]);
                
                if (!row) return await message.reply("❌ Промокод не существует или исчерпан.", replyParams());
                
                const usedBy = row.used_by ? row.used_by.split(",") : [];
                if (usedBy.length >= row.limit_count) {
                    await dbRun("DELETE FROM promos WHERE code = ?", [parts[1]]);
                    return await message.reply("❌ Промокод больше не действителен.", replyParams());
                }
                
                if (usedBy.includes(String(userId))) return await message.reply("❌ Ты уже активировал этот промокод!", replyParams());
                
                usedBy.push(String(userId));
                await updateBalance(userId, row.amount);
                
                if (usedBy.length >= row.limit_count) {
                    await dbRun("DELETE FROM promos WHERE code = ?", [parts[1]]);
                    return await message.reply(`✅ Активирован! +${row.amount}$\n⚠️ Промокод удален (лимит исчерпан).`, replyParams());
                } else {
                    await dbRun("UPDATE promos SET used_by = ? WHERE code = ?", [usedBy.join(","), parts[1]]);
                    return await message.reply(`✅ Активирован! +${row.amount}$\nОсталось: ${row.limit_count - usedBy.length}`, replyParams());
                }
            } else {
                return await message.reply("❌ Формат: /promo [код]", replyParams());
            }
        }

        return;

    } catch (error) {
        console.error("ОШИБКА ПРИ ОБРАБОТКЕ:", error);
        try { await message.reply(`⚠️ Произошла ошибка при выполнении команды: ${error.message}`, { disable_mentions: 1 }); } catch (e) {}
    }
});

// ===== ОБРАБОТКА КНОПОК =====
vk.updates.on('message_event', async (context) => {
    try {
        const payload = context.eventPayload;
        const userId = context.userId;
        
        if (payload.cmd === 'activate_bot' || payload.cmd === 'decline_bot') {
            try {
                const members = await vk.api.messages.getConversationMembers({ peer_id: context.peerId });
                const clicker = members.items.find(m => m.member_id === userId);
                const isClickerAdmin = clicker && (clicker.is_admin || clicker.is_owner);
                
                if (!isClickerAdmin && userId !== ADMIN_ID) {
                    return await context.answer({ type: 'show_snackbar', text: '❌ Только администраторы беседы могут это сделать!' });
                }

                const bot = members.items.find(m => m.member_id == -GROUP_ID || m.member_id == GROUP_ID);
                const isBotAdmin = bot && bot.is_admin;

                if (payload.cmd === 'activate_bot') {
                    if (!isBotAdmin) return await context.answer({ type: 'show_snackbar', text: '❌ Ошибка. Убедитесь, что бот владеет статусом администратора.' });
                    await context.answer({ type: 'show_snackbar', text: '✅ Бот успешно активирован!' });
                    await context.editMessage({ message: "🎉 Вы подключили бота к беседе!\nЧтобы узнать подробности напишите /help" });
                } else {
                    await context.answer({ type: 'show_snackbar', text: 'Активация отменена.' });
                    await context.editMessage({ message: "❌ Активация отменена. Чтобы начать работу, добавьте бота заново." });
                }
                return;
            } catch (e) {
                return await context.answer({ type: 'show_snackbar', text: '❌ Ошибка при проверке прав.' });
            }
        }

        // ===== КНОПКИ БИЗНЕСА =====
        if (payload.cmd.startsWith('biz_')) {
            if (String(context.userId) !== String(payload.author)) return await context.answer({ type: 'show_snackbar', text: '❌ Это не ваш бизнес!' });
            
            const biz = await dbGet("SELECT * FROM businesses WHERE user_id = ?", [String(userId)]);
            if (!biz) return await context.answer({ type: 'show_snackbar', text: '❌ У вас нет бизнеса.' });

            const bizData = Object.values(BIZ_DATA).find(b => b.name === biz.biz_name) || { name: biz.biz_name, baseIncome: 1000 };
            const timePassed = Date.now() - biz.last_income;
            const earned = Math.floor(timePassed * ((bizData.baseIncome * biz.level) / 180000));
            const totalBalance = Number(biz.balance) + earned;

            if (payload.cmd === 'biz_withdraw') {
                if (totalBalance <= 0) return await context.answer({ type: 'show_snackbar', text: '❌ Нечего выводить!' });
                await updateBalance(userId, totalBalance);
                await dbRun("UPDATE businesses SET balance = 0, last_income = ? WHERE user_id = ?", [Date.now(), String(userId)]);
                await context.answer({ type: 'show_snackbar', text: `✅ Выведено ${formatMoney(totalBalance)}$!` });
                await context.editMessage({ message: `🏢 Бизнес ${biz.biz_name}\n\n💵 Вы успешно вывели ${formatMoney(totalBalance)}$ на баланс!`, keyboard: getBizKb(userId) });
                return;
            }

            if (payload.cmd === 'biz_upgrade') {
                const nextLevelCost = (biz.level === 1 ? 2000000 : biz.level === 2 ? 5000000 : biz.level * 5000000);
                const userBal = await getBalance(userId);
                if (biz.level >= 5) return await context.answer({ type: 'show_snackbar', text: '❌ Максимальный уровень!' });
                if (userBal < nextLevelCost) return await context.answer({ type: 'show_snackbar', text: '❌ Не хватает денег на балансе!' });

                await updateBalance(userId, -nextLevelCost);
                await dbRun("UPDATE businesses SET level = level + 1, balance = ?, last_income = ? WHERE user_id = ?", [totalBalance, Date.now(), String(userId)]);
                await context.answer({ type: 'show_snackbar', text: `✅ Уровень повышен до ${biz.level + 1}!` });
                
                const newBizData = { name: biz.biz_name, baseIncome: bizData.baseIncome };
                await context.editMessage({ message: `🏢 Бизнес ${biz.biz_name}\n\n💪 Новый уровень: ${biz.level + 1}\n📈 Доход: ${formatMoney(newBizData.baseIncome * (biz.level + 1))}$/3мин`, keyboard: getBizKb(userId) });
                return;
            }

            if (payload.cmd === 'biz_close') {
                await updateBalance(userId, 10000000);
                await dbRun("DELETE FROM businesses WHERE user_id = ?", [String(userId)]);
                await context.answer({ type: 'show_snackbar', text: '💀 Бизнес закрыт. Вы получили 10,000,000$' });
                await context.editMessage({ message: `💀 Вы закрыли бизнес и получили компенсацию 10,000,000$.`, keyboard: "" });
                return;
            }
        }

        // ===== КНОПКИ ТОПОВ =====
        if (payload.cmd === 'top_menu') {
            if (String(context.userId) !== String(payload.author)) {
                return await context.answer({ type: 'show_snackbar', text: '❌ Это меню вызвано другим пользователем.' });
            }

            const type = payload.type;
            const scope = payload.scope;
            const repType = payload.repType || 'pos';

            let orderBy = "balance DESC";
            let filter = "balance > 2";
            
            if (type === 'rep') {
                orderBy = repType === 'pos' ? "reputation DESC" : "reputation ASC";
                filter = "reputation != 0";
            } else if (type === 'level') {
                orderBy = "level DESC, xp DESC";
                filter = "level > 1"; 
            }

            let rows = [];
            if (scope === 'global') {
                rows = await dbAll(`SELECT user_id, balance, reputation, level, xp FROM users WHERE ${filter} ORDER BY ${orderBy} LIMIT 10`);
            } else {
                // Топ в беседе (используем chat_messages для связи, сортируем по данным из users)
                const chatUsers = await dbAll("SELECT user_id FROM chat_messages WHERE peer_id = ?", [String(context.peerId)]);
                if (chatUsers.length > 0) {
                    const ids = chatUsers.map(u => `'${u.user_id}'`).join(',');
                    rows = await dbAll(`SELECT user_id, balance, reputation, level, xp FROM users WHERE user_id IN (${ids}) AND ${filter} ORDER BY ${orderBy} LIMIT 10`);
                }
            }

            if (rows.length === 0) return await context.answer({ type: 'show_snackbar', text: '❌ Топ пуст.' });

            const userIds = rows.map(r => r.user_id);
            let usersInfo = [];
            try { usersInfo = await vk.api.users.get({ user_ids: userIds.join(','), fields: 'deactivated' }); } catch (e) {}

            let title = `🏆 ТОП 10 (${scope === 'global' ? 'Общий' : 'В беседе'})\n`;
            if (type === 'coins') title += "💰 По монетам\n\n";
            if (type === 'level') title += "📊 По уровню\n\n";
            if (type === 'rep') title += `⭐ По репутации (${repType === 'pos' ? 'Положительная' : 'Отрицательная'})\n\n`;

            let topText = title;
            let count = 0;
            const emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"];
            
            for (const r of rows) {
                const uInfo = usersInfo.find(u => u.id == r.user_id);
                if (uInfo && !uInfo.deactivated) {
                    let value = "";
                    if (type === 'coins') value = `${formatMoney(r.balance)}$`;
                    if (type === 'level') value = `Ур. ${r.level} (${r.xp} XP)`;
                    if (type === 'rep') value = `${r.reputation > 0 ? '+' : ''}${r.reputation}`;
                    
                    topText += `${emojis[count]} [id${uInfo.id}|${uInfo.first_name} ${uInfo.last_name || ''}] — ${value}\n`;
                    count++;
                }
            }

            await context.answer();
            await vk.api.messages.edit({
                peer_id: context.peerId,
                conversation_message_id: context.conversationMessageId,
                message: topText,
                keyboard: getTopKb(payload.author, type, scope, repType)
            });
            return;
        }

        // ===== ИГРЫ (КНОПКИ) =====
        if (payload.cmd === 'duel_accept') {
            const duelId = payload.duel_id;
            const row = await dbGet("SELECT challenger, bet FROM active_duels WHERE msg_id = ?", [duelId]);
            
            if (row) {
                if (String(userId) === row.challenger) return await context.answer({ type: 'show_snackbar', text: '❌ Нельзя драться с собой!' });
                if (await getBalance(userId) < row.bet) return await context.answer({ type: 'show_snackbar', text: '❌ Не хватает денег!' });
                
                const winnerId = Math.random() < 0.5 ? parseInt(row.challenger) : userId;
                const loserId = winnerId === userId ? parseInt(row.challenger) : userId;
                const prize = Math.floor(row.bet * 1.8);
                
                await updateBalance(winnerId, prize);
                await updateBalance(loserId, -row.bet);
                await dbRun("DELETE FROM active_duels WHERE msg_id = ?", [duelId]);
                
                const winnerName = await getFullName(winnerId);
                const loserName = await getFullName(loserId);
                const msgText = `⚔️ Дуэль завершена!\n\n🏆 Победитель: ${winnerName}\n❌ Проигравший: ${loserName}\n\n💰 Выигрыш: ${prize}$`;
                
                await context.answer({ type: 'show_snackbar', text: '⚔️ Дуэль завершена!' });
                
                await vk.api.messages.edit({
                    peer_id: context.peerId,
                    conversation_message_id: context.conversationMessageId,
                    message: msgText,
                    keyboard: ""
                });
                return;
            }
        }

        if (payload.cmd === 'mines_set') {
            const gameId = String(payload.gameId);
            const count = Number(payload.count);
            
            const row = await dbGet("SELECT bet FROM games WHERE game_id = ? AND user_id = ?", [gameId, String(userId)]);
            if (!row) return await context.answer({ type: 'show_snackbar', text: '❌ Это не ваша игра!' });

            const minesArr = [];
            while(minesArr.length < count) {
                const r = Math.floor(Math.random() * 9) + 1;
                if (!minesArr.includes(r)) minesArr.push(r);
            }
            const minesStr = JSON.stringify(minesArr);
            await dbRun("UPDATE games SET mines = ?, opened = '[]', multiplier = 1.0 WHERE game_id = ?", [minesStr, gameId]);
            
            const msgText = `💣 Мины\nСтавка: ${row.bet}$ | Мин: ${count} из 9\n\nВыбери клетку, чтобы открыть алмаз 💎`;
            
            await context.answer(); 
            
            await vk.api.messages.edit({
                peer_id: context.peerId,
                conversation_message_id: context.conversationMessageId,
                message: msgText,
                keyboard: getMinesFieldKb(gameId, [], minesArr)
            });
            return;
        }

        if (payload.cmd === 'mines_click') {
            const gameId = String(payload.gameId);
            const cell = Number(payload.cell);
            
            const row = await dbGet("SELECT bet, mines, opened, multiplier FROM games WHERE game_id = ? AND user_id = ?", [gameId, String(userId)]);
            
            if (!row) return await context.answer({ type: 'show_snackbar', text: '❌ Это не ваша игра или она уже завершена.' });

            const bet = row.bet;
            const mines = JSON.parse(row.mines);
            const opened = JSON.parse(row.opened);
            
            if (opened.includes(cell)) return await context.answer({ type: 'show_snackbar', text: '❌ Клетка уже открыта!' });

            opened.push(cell);

            if (mines.includes(cell)) {
                await updateBalance(userId, -bet);
                await dbRun("DELETE FROM games WHERE game_id = ?", [gameId]);
                
                const msgText = `💥 Вы попали на мину!\n\nПроигрыш: -${bet}$\nБаланс: ${formatMoney(await getBalance(userId))}$`;
                
                await context.answer({ type: 'show_snackbar', text: '💥 БУМ! Вы проиграли.' });
                
                await vk.api.messages.edit({
                    peer_id: context.peerId,
                    conversation_message_id: context.conversationMessageId,
                    message: msgText,
                    keyboard: getMinesFieldKb(gameId, Array.from({length: 9}, (_, i) => i + 1), mines, true)
                });
                return;
            }

            let newMult = 1.0;
            for (let i = 0; i < opened.length; i++) {
                newMult *= (9 - i) / (9 - mines.length - i);
            }
            newMult = Math.round(newMult * 0.95 * 100) / 100;
            
            await dbRun("UPDATE games SET opened = ?, multiplier = ? WHERE game_id = ?", [JSON.stringify(opened), newMult, gameId]);
            
            const winAmount = Math.floor(bet * newMult);
            const msgText = `💣 Мины\nСтавка: ${bet}$ | Мин: ${mines.length} из 9\n\nОткрыто алмазов: ${opened.length} | Коэф: x${newMult}\nВыигрыш сейчас: ${winAmount}$`;
            
            await context.answer({ type: 'show_snackbar', text: `💎 Алмаз! x${newMult}` });
            
            await vk.api.messages.edit({
                peer_id: context.peerId,
                conversation_message_id: context.conversationMessageId,
                message: msgText,
                keyboard: getMinesFieldKb(gameId, opened, mines)
            });
            return;
        }

        if (payload.cmd === 'mines_cashout') {
            const gameId = String(payload.gameId);
            const row = await dbGet("SELECT bet, multiplier, mines FROM games WHERE game_id = ? AND user_id = ?", [gameId, String(userId)]);
            
            if (!row) return await context.answer({ type: 'show_snackbar', text: '❌ Это не ваша игра или она уже завершена.' });

            if (!row.mines || row.mines === '[]') {
                return await context.answer({ type: 'show_snackbar', text: '❌ Игра еще не началась!' });
            }

            const winAmount = Math.floor(row.bet * row.multiplier);
            await updateBalance(userId, winAmount);
            await dbRun("DELETE FROM games WHERE game_id = ?", [gameId]);
            
            const msgText = `💰 Вы забрали выигрыш: ${winAmount}$!\nБаланс: ${formatMoney(await getBalance(userId))}$`;
            
            await vk.api.messages.edit({
                peer_id: context.peerId,
                conversation_message_id: context.conversationMessageId,
                message: msgText,
                keyboard: ""
            });
            return await context.answer({ type: 'show_snackbar', text: `💰 Вы забрали ${winAmount}$!` });
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
