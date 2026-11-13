const { VK, Keyboard } = require('vk-io');
const sqlite3 = require('sqlite3').verbose();
const fs = require('fs');
const path = require('path');

console.log("=========================================");
console.log("ВЕРСИЯ NODE.JS:", process.version);
console.log("=========================================");

// ===== НАСТРОЙКИ =====
const TOKEN = "vk1.a.BvMZnZvhxLsOu5bIQ1IUIIoYMEW3T88NqEAcRZ17Yj-T46O-viFXkUPWky-4XBwNZAKsWhcwqAt3TDMqQmcKva0ckucYDEUvFKa_p_LJ9ig-zNIPv7cHSZV9KP4S8XLgO0m32YWDLuqfz-rqgrrhoFKZ0mexTvf71NQ5G1JVI0H7QtuL4HGdtQkAvT7Up8xnC-vaO3QTue9x8V5a3u1-DuwMwEXIvfB4OgnVo0_FXGI";
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

async function initDB() {
    await dbRun("CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, balance INTEGER DEFAULT 1000000, rep INTEGER DEFAULT 0)");
    await dbRun("CREATE TABLE IF NOT EXISTS active_duels (msg_id TEXT PRIMARY KEY, challenger TEXT, bet INTEGER, peer_id TEXT)");
    await dbRun("CREATE TABLE IF NOT EXISTS bonus_cd (user_id TEXT PRIMARY KEY, last_used INTEGER)");
    await dbRun("CREATE TABLE IF NOT EXISTS fortune_cd (user_id TEXT PRIMARY KEY, last_used INTEGER)");
    await dbRun("CREATE TABLE IF NOT EXISTS promos (code TEXT PRIMARY KEY, amount INTEGER, limit_count INTEGER, used_by TEXT DEFAULT '')");
    await dbRun("CREATE TABLE IF NOT EXISTS games (game_id TEXT PRIMARY KEY, user_id TEXT, bet INTEGER, mines TEXT, opened TEXT, multiplier REAL, msg_id TEXT)");
    await dbRun("CREATE TABLE IF NOT EXISTS blacklist (user_id TEXT PRIMARY KEY, reason TEXT)");
    await dbRun("CREATE TABLE IF NOT EXISTS chat_messages (peer_id TEXT, user_id TEXT, count INTEGER DEFAULT 0, PRIMARY KEY (peer_id, user_id))");
    await dbRun("CREATE TABLE IF NOT EXISTS activated_chats (peer_id TEXT PRIMARY KEY)");
    await dbRun("CREATE TABLE IF NOT EXISTS user_businesses (user_id TEXT PRIMARY KEY, biz_id INTEGER, level INTEGER DEFAULT 1, last_collect INTEGER DEFAULT 0)");
    await dbRun("CREATE TABLE IF NOT EXISTS rep_cooldown (user_id TEXT, target_id TEXT, last_used INTEGER, PRIMARY KEY (user_id, target_id))");
    console.log("--- БАЗА ДАННЫХ ГОТОВА ---");
}
initDB();

// ===== ХЕЛПЕРЫ =====
async function getUser(userId) {
    let row = await dbGet("SELECT * FROM users WHERE user_id = ?", [String(userId)]);
    if (!row) {
        await dbRun("INSERT INTO users (user_id, balance, rep) VALUES (?, 1000000, 0)", [String(userId)]);
        return { user_id: String(userId), balance: 1000000, rep: 0 };
    }
    return row;
}

async function updateBalance(userId, amount) {
    const u = await getUser(userId);
    await dbRun("UPDATE users SET balance = ? WHERE user_id = ?", [u.balance + amount, String(userId)]);
}

async function updateRep(userId, amount) {
    const u = await getUser(userId);
    await dbRun("UPDATE users SET rep = ? WHERE user_id = ?", [u.rep + amount, String(userId)]);
}

async function getFullName(userId) {
    try {
        const [user] = await vk.api.users.get({ user_ids: userId });
        return `[id${userId}|${user.first_name} ${user.last_name || ''}]`;
    } catch { return `[id${userId}|Игрок]`; }
}

function formatMoney(num) { return num.toLocaleString('ru-RU'); }

// ===== БИЗНЕСЫ =====
const BIZNESSES = [
    { id: 1, name: "шаурмичная", price: 500000000000, income: 500000000, photo: "-243089386_457239017" },
    { id: 2, name: "кафе", price: 1000000000000, income: 1000000000, photo: "-243089386_457239018" },
    { id: 3, name: "большое кафе", price: 5000000000000, income: 7000000000, photo: "-243089386_457239019" },
    { id: 4, name: "хлебопекарня", price: 10000000000000, income: 6000000000, photo: "-243089386_457239020" },
    { id: 5, name: "ресторан", price: 20000000000000, income: 50000000000, photo: "-243089386_457239021" },
    { id: 6, name: "отель", price: 50000000000000, income: 100000000000, photo: "-243089386_457239022" },
    { id: 7, name: "сеть отелей", price: 300000000000000, income: 500000000000, photo: "-243089386_457239023" },
    { id: 8, name: "казик", price: 800000000000000, income: 1000000000000, photo: "-243089386_457239024" },
    { id: 9, name: "страна", price: 2000000000000000, income: 3000000000000, photo: "-243089386_457239025" }
];

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
            kb.callbackButton({ 
                label: mines.includes(i) ? '💥' : '💎', 
                payload: { cmd: 'none' }, 
                color: mines.includes(i) ? Keyboard.NEGATIVE_COLOR : Keyboard.POSITIVE_COLOR 
            });
        } else {
            kb.callbackButton({ 
                label: String(i), 
                payload: isGameOver ? { cmd: 'none' } : { cmd: 'mines_click', gameId: String(gameId), cell: String(i) }, 
                color: Keyboard.SECONDARY_COLOR 
            });
        }
        if (i % 3 === 0) kb.row();
    }
    
    if (!isGameOver) {
        kb.callbackButton({ label: '💰 Забрать', payload: { cmd: 'mines_cashout', gameId: String(gameId) }, color: Keyboard.POSITIVE_COLOR });
    }
    return kb.toString();
};

const getTopMsgKb = () => Keyboard.builder().inline().callbackButton({
    label: '💰 Топ по монетам', payload: { cmd: 'top_coins' }, color: Keyboard.SECONDARY_COLOR
}).toString();

const getTopCoinsKb = () => Keyboard.builder().inline().callbackButton({
    label: '🔙 Назад', payload: { cmd: 'top_messages' }, color: Keyboard.SECONDARY_COLOR
}).toString();

// ===== ОБРАБОТКА СООБЩЕНИЙ =====
vk.updates.on('chat_invite_user', async (context) => {
    if (String(context.memberId) === String(-GROUP_ID)) {
        try {
            await vk.api.messages.send({
                peer_id: context.peerId,
                message: "👋 Добро пожаловать! Я официальный игровой бот Game Zone.\n\nДля активации выдайте мне права администратора и напишите /start",
                random_id: Math.floor(Math.random() * 1000000000),
                group_id: GROUP_ID,
                disable_mentions: 1
            });
        } catch (err) { console.error(`[ОШИБКА ПРИВЕТСТВИЯ]`, err); }
    }
});

vk.updates.on('message_new', async (message) => {
    if (message.isOutbox) return;
    if (message.senderId < 0) return;

    try {
        const text = message.text ? message.text.trim().toLowerCase() : '';
        if (!text) return;

        if (message.isChat) {
            const existing = await dbGet("SELECT count FROM chat_messages WHERE peer_id = ? AND user_id = ?", [String(message.peerId), String(message.senderId)]);
            if (existing) await dbRun("UPDATE chat_messages SET count = count + 1 WHERE peer_id = ? AND user_id = ?", [String(message.peerId), String(message.senderId)]);
            else await dbRun("INSERT INTO chat_messages (peer_id, user_id, count) VALUES (?, ?, 1)", [String(message.peerId), String(message.senderId)]);
        }

        if (text.startsWith('/')) {
            const isBlacklisted = await dbGet("SELECT reason FROM blacklist WHERE user_id = ?", [String(message.senderId)]);
            if (isBlacklisted) return await message.reply(`🚫 Вы в ЧС. Причина: ${isBlacklisted.reason}`, { disable_mentions: 1 });
        }

        if (!text.startsWith('/') && text !== '💼 работа') return;

        const cleanText = text.replace(/\//g, '').trim();
        const parts = cleanText.split(/\s+/);
        const userId = message.senderId;
        const peerId = message.peerId;
        const isLs = peerId === userId;
        const user = await getUser(userId);

        const replyParams = (kb = undefined) => {
            const p = { disable_mentions: 1 };
            if (kb) p.keyboard = kb;
            return p;
        };

        // --- КОМАНДЫ ---
        if (text.includes('начать') || text.includes('start')) {
            if (!message.isChat) return await message.reply("👋 Привет! Я игровой бот. Выбирай действие на клавиатуре или напиши /help.", replyParams(mainKb));
            
            const peerIdStr = String(peerId);
            const isActivated = await dbGet("SELECT peer_id FROM activated_chats WHERE peer_id = ?", [peerIdStr]);
            if (isActivated) return await message.reply("✅ Бот уже активирован! Напиши /help для списка команд.", replyParams());

            try {
                const members = await vk.api.messages.getConversationMembers({ peer_id: peerId });
                const member = members.items.find(m => m.member_id == userId);
                const bot = members.items.find(m => m.member_id == -GROUP_ID || m.member_id == GROUP_ID);
                if (!member || (!member.is_admin && !member.is_owner)) return await message.reply("❌ У вас нет прав администратора.", replyParams());
                if (!bot || !bot.is_admin) return await message.reply("❌ Выдайте боту права администратора.", replyParams());
                
                await dbRun("INSERT INTO activated_chats (peer_id) VALUES (?)", [peerIdStr]);
                return await message.reply("✅ Бот успешно активирован! Напишите /help.", replyParams());
            } catch (e) { return await message.reply("⚠️ Ошибка проверки прав.", replyParams()); }
        }

        if (text.includes('help') || text.includes('помощь') || text.includes('команды')) {
            const helpText = "📖 Команды:\n🎰 /рулетка [цвет/чет] [ставка]\n🎲 /фортуна (100$)\n💣 /мины [ставка]\n⚔️ /duel [сумма]\n💸 /transfer [сумма] (ответом)\n🎁 /бонус\n🎁 /promo [код]\n📜 /промолист\n🕵️ /мафия (Игра)\n📊 /rep +/- (Репутация)\n🏢 /бизнес\n👤 /профиль\n🏆 /топ";
            return await message.reply(helpText, replyParams(isLs ? mainKb : undefined));
        }

        if (text === '💼 работа') {
            const earned = Math.floor(Math.random() * 400) + 100;
            await updateBalance(userId, earned);
            return await message.reply(`✅ Заработано ${earned}$!\n💰 Баланс: ${formatMoney((await getUser(userId)).balance)}$`, replyParams(isLs ? mainKb : undefined));
        }

        if (cleanText === 'профиль' || cleanText === 'баланс') {
            return await message.reply(`👤 Профиль:\n💰 Баланс: ${formatMoney(user.balance)}$\n📊 Репутация: ${user.rep}\n🆔 ID: ${userId}`, replyParams(isLs ? mainKb : undefined));
        }

        if (cleanText === 'топ' || cleanText === 'top') {
            if (isLs) return await message.reply("❌ Только в беседах!", replyParams());
            const rows = await dbAll("SELECT user_id, count FROM chat_messages WHERE peer_id = ? ORDER BY count DESC LIMIT 10", [String(peerId)]);
            if (rows.length === 0) return await message.reply("🏆 Пусто.", replyParams());
            let topText = "⭐ ТОП 10 ПО СООБЩЕНИЯМ\n\n", count = 0;
            const emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"];
            for (const r of rows) {
                const uInfo = (await vk.api.users.get({ user_ids: r.user_id, fields: 'deactivated' }))[0];
                if (uInfo && !uInfo.deactivated) {
                    topText += `${emojis[count]} [id${uInfo.id}|${uInfo.first_name}] - ${r.count} сообщений\n`;
                    count++;
                }
            }
            return await message.reply(topText, replyParams(getTopMsgKb()));
        }

        // ===== РЕПУТАЦИЯ =====
        if (cleanText.startsWith('rep')) {
            const sign = parts[1];
            if (!sign || (!sign.includes('+') && !sign.includes('-'))) return await message.reply("❌ Формат: /rep + @user или /rep - @user", replyParams());
            
            let targetId = null;
            if (message.hasReplyMessage) targetId = message.replyMessage.senderId;
            else {
                const match = message.text.match(/\[id(\d+)\|/i) || message.text.match(/@id(\d+)/i);
                if (match) targetId = parseInt(match[1]);
            }

            if (!targetId) return await message.reply("❌ Ответьте на сообщение или укажите пользователя через @.", replyParams());
            if (targetId === userId) return await message.reply("❌ Нельзя менять репутацию себе.", replyParams());

            const cd = await dbGet("SELECT last_used FROM rep_cooldown WHERE user_id = ? AND target_id = ?", [String(userId), String(targetId)]);
            if (cd && Date.now() / 1000 - cd.last_used < 86400) return await message.reply("⏳ Вы уже меняли репутацию этому пользователю сегодня.", replyParams());

            const amount = sign.includes('+') ? 1 : -1;
            await updateRep(targetId, amount);
            await dbRun("REPLACE INTO rep_cooldown (user_id, target_id, last_used) VALUES (?, ?, ?)", [String(userId), String(targetId), Math.floor(Date.now() / 1000)]);
            return await message.reply(`✅ Вы изменили репутацию ${await getFullName(targetId)} на ${amount > 0 ? '+1' : '-1'}.`, replyParams());
        }

        // ===== БИЗНЕС =====
        if (cleanText === 'бизнес') {
            const userBiz = await dbGet("SELECT * FROM user_businesses WHERE user_id = ?", [String(userId)]);
            if (userBiz) return await message.reply("❌ У вас уже есть бизнес! Напишите /мой_бизнес.", replyParams());

            const elements = BIZNESSES.map(b => ({
                title: b.name,
                description: `цена: ${formatMoney(b.price)}$\nзаработок: ${formatMoney(b.income)}$/час`,
                photo_id: b.photo,
                action: { type: 'open_photo' },
                buttons: [{ action: { type: 'callback', label: 'Купить', payload: { cmd: `buy_biz_${b.id}` } }, color: 'positive' }]
            }));

            const template = JSON.stringify({ type: 'carousel', elements: elements });
            
            try {
                await vk.api.messages.send({
                    peer_id: peerId,
                    message: "🏪 Магазин бизнесов (Листай вправо) 👉",
                    template: template,
                    random_id: Math.floor(Math.random() * 1000000)
                });
            } catch (e) {
                // Если ВК выдал ошибку из-за картинок, отправляем текстом
                let bizList = "🏪 Доступные бизнесы:\n\n";
                const kb = Keyboard.builder().inline();
                BIZNESSES.forEach(b => {
                    bizList += `${b.name} — ${formatMoney(b.price)}$ (${formatMoney(b.income)}$/час)\n`;
                    kb.callbackButton({ label: b.name, payload: { cmd: `buy_biz_${b.id}` } });
                });
                await message.reply(bizList, replyParams(kb.toString()));
            }
            return;
        }

        if (cleanText === 'мой_бизнес') {
            const userBiz = await dbGet("SELECT * FROM user_businesses WHERE user_id = ?", [String(userId)]);
            if (!userBiz) return await message.reply("❌ У вас нет бизнеса. Напишите /бизнес.", replyParams());
            
            const config = BIZNESSES.find(b => b.id === userBiz.biz_id);
            const currentIncome = config.income * userBiz.level;

            const kb = Keyboard.builder().inline()
                .callbackButton({ label: 'Вывести $$$', payload: { cmd: 'biz_collect' }, color: Keyboard.POSITIVE_COLOR }).row()
                .callbackButton({ label: 'Повысить уровень', payload: { cmd: 'biz_upgrade' }, color: Keyboard.PRIMARY_COLOR }).row()
                .callbackButton({ label: 'Закрыть бизнес', payload: { cmd: 'biz_close' }, color: Keyboard.NEGATIVE_COLOR });

            return await message.reply(`🏢 Бизнес: ${config.name}\n💪 Уровень: ${userBiz.level}/5\n😼 ${formatMoney(currentIncome)}$/час\n\nНажмите на кнопку:`, replyParams(kb.toString()));
        }

        // --- ОСТАЛЬНЫЕ ИГРЫ (РУЛЕТКА, ФОРТУНА, МИНЫ, ДУЭЛИ, ПРОМО) ---
        if (cleanText.startsWith('рулетка') || cleanText.startsWith('рул')) {
            if (parts.length >= 3) {
                const choice = parts[1];
                const betStr = parts[parts.length - 1];
                let bet = ['вб', 'всё', 'все'].includes(betStr) ? user.balance : parseInt(betStr);
                if (isNaN(bet) || bet < 10 || bet > user.balance) return await message.reply(`❌ Мин. 10, у тебя ${formatMoney(user.balance)}$`, replyParams());
                const res = Math.floor(Math.random() * 37);
                const red = [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36];
                let win = (parseInt(choice) === res) || (["красное", "кр"].includes(choice) && red.includes(res)) || (["черное", "чр"].includes(choice) && !red.includes(res) && res !== 0) || (["чет"].includes(choice) && res % 2 === 0 && res !== 0) || (["нечет"].includes(choice) && res % 2 !== 0);
                if (win) { await updateBalance(userId, bet); return await message.reply(`🎰 Выпало: ${res}. Выигрыш: +${bet}$`, replyParams(isLs ? mainKb : undefined)); }
                else { await updateBalance(userId, -bet); return await message.reply(`🎰 Выпало: ${res}. Проигрыш: -${bet}$`, replyParams(isLs ? mainKb : undefined)); }
            } else return await message.reply("❌ Формат: /рулетка красное 500", replyParams());
        }

        if (cleanText === 'фортуна') {
            const currentTime = Math.floor(Date.now() / 1000);
            const row = await dbGet("SELECT last_used FROM fortune_cd WHERE user_id = ?", [String(userId)]);
            if (row && currentTime - row.last_used < FORTUNA_CD) return await message.reply(`⏳ Ждите.`, replyParams());
            if (user.balance < 100) return await message.reply("❌ Стоит 100$.", replyParams());
            await updateBalance(userId, -100);
            await dbRun("REPLACE INTO fortune_cd (user_id, last_used) VALUES (?, ?)", [String(userId), currentTime]);
            const prize = [0, 50, 100, 200, 500, 1000, 5000][Math.floor(Math.random() * 7)];
            await updateBalance(userId, prize);
            return await message.reply(`🎰 Выпало: ${formatMoney(prize)}$!`, replyParams(isLs ? mainKb : undefined));
        }

        if (cleanText.startsWith('мины')) {
            let bet = 100;
            if (parts.length >= 2 && !isNaN(parts[1])) bet = parseInt(parts[1]);
            if (bet < 10 || bet > user.balance) return await message.reply(`❌ Мин. 10`, replyParams());
            const gameId = String(Math.floor(Math.random() * 90000) + 10000);
            await dbRun("INSERT INTO games (game_id, user_id, bet, mines, opened, multiplier, msg_id) VALUES (?, ?, ?, '[]', '[]', 1.0, ?)", [gameId, String(userId), bet, String(message.id)]);
            return await message.reply(`💣 Мины\nСтавка: ${bet}$\nВыберите кол-во мин:`, replyParams(getMinesCountKb(gameId)));
        }

        if (cleanText === 'бонус') {
            const currentTime = Math.floor(Date.now() / 1000);
            const row = await dbGet("SELECT last_used FROM bonus_cd WHERE user_id = ?", [String(userId)]);
            if (row && currentTime - row.last_used < BONUS_CD) return await message.reply(`⏳ Ждите.`, replyParams());
            const amount = [100000, 200000, 500000][Math.floor(Math.random() * 3)];
            await updateBalance(userId, amount);
            await dbRun("REPLACE INTO bonus_cd (user_id, last_used) VALUES (?, ?)", [String(userId), currentTime]);
            return await message.reply(`🎁 Бонус: +${formatMoney(amount)}$`, replyParams(isLs ? mainKb : undefined));
        }

        // ===== МАФИЯ =====
        if (cleanText === 'мафия') {
            if (isLs) return await message.reply("❌ Только в беседах!", replyParams());
            
            const hostName = await getFullName(userId);
            const mafiaKb = Keyboard.builder().inline()
                .callbackButton({ label: 'Войти 📨', payload: { cmd: 'mafia_join' }, color: Keyboard.POSITIVE_COLOR })
                .callbackButton({ label: 'Выйти 📨', payload: { cmd: 'mafia_leave' }, color: Keyboard.NEGATIVE_COLOR }).row()
                .callbackButton({ label: '🚀 Начать игру', payload: { cmd: 'mafia_start' }, color: Keyboard.PRIMARY_COLOR })
                .callbackButton({ label: '❌ Отмена', payload: { cmd: 'mafia_cancel' }, color: Keyboard.SECONDARY_COLOR }).row()
                .urlButton({ label: '✉️ Написать боту', url: `https://vk.com/write-${GROUP_ID}` });

            return await message.reply(`🎭 МАФИЯ — регистрация\n\n👑 Ведущий: ${hostName}\n\nНужно минимум 4 игрока. Роли придут в ЛС!\nНажмите "Войти", чтобы участвовать.`, replyParams(mafiaKb.toString()));
        }

        // ===== АДМИНКА =====
        if (userId === ADMIN_ID) {
            if (cleanText.startsWith('kick')) {
                let targetId = message.hasReplyMessage ? message.replyMessage.senderId : null;
                if (!targetId) return await message.reply("⚠️ Ответьте на сообщение.", replyParams());
                if (!message.isChat) return await message.reply("❌ Только в беседах.", replyParams());
                try {
                    await vk.api.messages.removeChatUser({ chat_id: peerId - 2000000000, user_id: targetId, group_id: GROUP_ID });
                    return await message.reply(`✅ Пользователь исключен.`, replyParams());
                } catch (e) { return await message.reply(`⚠️ Ошибка.`, replyParams()); }
            }
            if (cleanText.startsWith('чсб')) {
                let targetId = message.hasReplyMessage ? message.replyMessage.senderId : null;
                if (!targetId) return await message.reply("⚠️ Ответьте на сообщение.", replyParams());
                await dbRun("REPLACE INTO blacklist (user_id, reason) VALUES (?, ?)", [String(targetId), parts.slice(1).join(' ') || 'Без причины']);
                return await message.reply(`✅ В ЧС.`, replyParams());
            }
            if (cleanText.startsWith('деньги')) {
                if (parts.length === 2 && !isNaN(parts[1]) && message.hasReplyMessage) {
                    await updateBalance(message.replyMessage.senderId, parseInt(parts[1]));
                    return await message.reply(`✅ Выдано.`, replyParams());
                }
            }
            if (cleanText.startsWith('создать')) {
                if (parts.length === 4 && !isNaN(parts[2]) && !isNaN(parts[3])) {
                    await dbRun("REPLACE INTO promos (code, amount, limit_count, used_by) VALUES (?, ?, ?, '')", [parts[1], parseInt(parts[2]), parseInt(parts[3])]);
                    return await message.reply(`✅ Промокод создан.`, replyParams());
                }
            }
            if (cleanText === 'cp') {
                await dbRun("DELETE FROM promos");
                return await message.reply("✅ Промо удалены.", replyParams());
            }
        }

        if (cleanText === 'промолист') {
            const rows = await dbAll("SELECT code, amount, limit_count, used_by FROM promos");
            if (rows.length === 0) return await message.reply("❌ Пусто.", replyParams());
            let list = "🎁 Промокоды:\n\n";
            for (const r of rows) list += `▪️ ${r.code} — ${r.amount}$\n`;
            return await message.reply(list, replyParams());
        }

        if (cleanText.startsWith('promo')) {
            if (parts.length === 2) {
                const row = await dbGet("SELECT * FROM promos WHERE code = ?", [parts[1]]);
                if (!row) return await message.reply("❌ Неверный код.", replyParams());
                const usedBy = row.used_by ? row.used_by.split(",") : [];
                if (usedBy.includes(String(userId))) return await message.reply("❌ Вы уже активировали.", replyParams());
                usedBy.push(String(userId));
                await updateBalance(userId, row.amount);
                await dbRun("UPDATE promos SET used_by = ? WHERE code = ?", [usedBy.join(","), parts[1]]);
                return await message.reply(`✅ Активирован! +${row.amount}$`, replyParams());
            }
        }

    } catch (error) {
        console.error("ОШИБКА:", error);
    }
});

// ===== ОБРАБОТКА КНОПОК =====
vk.updates.on('message_event', async (context) => {
    try {
        const payload = context.eventPayload;
        const userId = context.userId;
        const chatId = context.peerId;
        
        // --- БИЗНЕСЫ ---
        if (payload.cmd && payload.cmd.startsWith('buy_biz_')) {
            const bizId = parseInt(payload.cmd.split('_')[2]);
            const biz = BIZNESSES.find(b => b.id === bizId);
            const userBiz = await dbGet("SELECT * FROM user_businesses WHERE user_id = ?", [String(userId)]);
            if (userBiz) return await context.answer({ type: 'show_snackbar', text: '❌ У вас уже есть бизнес!' });
            
            const user = await getUser(userId);
            if (user.balance < biz.price) return await context.answer({ type: 'show_snackbar', text: '❌ Недостаточно денег!' });

            await updateBalance(userId, -biz.price);
            await dbRun("INSERT INTO user_businesses (user_id, biz_id) VALUES (?, ?)", [String(userId), bizId]);
            return await context.answer({ type: 'show_snackbar', text: `✅ Вы купили ${biz.name}!` });
        }

        if (payload.cmd === 'biz_collect') {
            const userBiz = await dbGet("SELECT * FROM user_businesses WHERE user_id = ?", [String(userId)]);
            if (!userBiz) return await context.answer({ type: 'show_snackbar', text: '❌ У вас нет бизнеса.' });
            const biz = BIZNESSES.find(b => b.id === userBiz.biz_id);
            const income = biz.income * userBiz.level;
            await updateBalance(userId, income);
            return await context.answer({ type: 'show_snackbar', text: `💰 Выведено: ${formatMoney(income)}$!` });
        }

        if (payload.cmd === 'biz_upgrade') {
            const userBiz = await dbGet("SELECT * FROM user_businesses WHERE user_id = ?", [String(userId)]);
            if (userBiz.level >= 5) return await context.answer({ type: 'show_snackbar', text: '❌ Максимальный уровень!' });
            const biz = BIZNESSES.find(b => b.id === userBiz.biz_id);
            const cost = biz.price * userBiz.level;
            const user = await getUser(userId);
            if (user.balance < cost) return await context.answer({ type: 'show_snackbar', text: '❌ Не хватает денег на улучшение!' });
            await updateBalance(userId, -cost);
            await dbRun("UPDATE user_businesses SET level = level + 1 WHERE user_id = ?", [String(userId)]);
            return await context.answer({ type: 'show_snackbar', text: `✅ Уровень повышен до ${userBiz.level + 1}!` });
        }

        if (payload.cmd === 'biz_close') {
            const userBiz = await dbGet("SELECT * FROM user_businesses WHERE user_id = ?", [String(userId)]);
            if (!userBiz) return await context.answer({ type: 'show_snackbar', text: '❌ У вас нет бизнеса.' });
            const biz = BIZNESSES.find(b => b.id === userBiz.biz_id);
            const refund = Math.floor(biz.price * 0.5);
            await updateBalance(userId, refund);
            await dbRun("DELETE FROM user_businesses WHERE user_id = ?", [String(userId)]);
            return await context.answer({ type: 'show_snackbar', text: `✅ Бизнес закрыт. Возврат: ${formatMoney(refund)}$` });
        }

        // --- МАФИЯ ---
        if (payload.cmd && payload.cmd.startsWith('mafia_')) {
            if (payload.cmd === 'mafia_join') {
                try {
                    await vk.api.messages.send({ peer_id: userId, message: '✅ Вы вошли в игру Мафия!', random_id: Math.floor(Math.random() * 1000000) });
                    return await context.answer({ type: 'show_snackbar', text: '✅ Вы вошли в игру!' });
                } catch (e) {
                    return await context.answer({ type: 'show_snackbar', text: '⚠️ Напишите боту в ЛС! (Кнопка внизу)' });
                }
            }
            if (payload.cmd === 'mafia_start') {
                const host = await getFullName(userId); // Simplified check
                // В реальном коде проверяем, что userId == hostId
                return await context.answer({ type: 'show_snackbar', text: '🚀 Игра началась! Роли отправлены в ЛС.' });
            }
            if (payload.cmd === 'mafia_cancel') {
                return await context.answer({ type: 'show_snackbar', text: '❌ Игра отменена.' });
            }
        }

        // --- ТОПЫ ---
        if (payload.cmd === 'top_coins') {
            const rows = await dbAll("SELECT user_id, balance FROM users ORDER BY balance DESC LIMIT 10");
            let text = "🏆 Топ 10 богачей:\n\n";
            let c = 1;
            for (const r of rows) {
                text += `${c}. ${await getFullName(r.user_id)} — ${formatMoney(r.balance)}$\n`;
                c++;
            }
            await context.editMessage({ message: text, keyboard: getTopCoinsKb() });
            return await context.answer();
        }
        if (payload.cmd === 'top_messages') {
            const rows = await dbAll("SELECT user_id, count FROM chat_messages WHERE peer_id = ? ORDER BY count DESC LIMIT 10", [String(context.peerId)]);
            let text = "⭐ ТОП 10 ПО СООБЩЕНИЯМ\n\n";
            let c = 0;
            const emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"];
            for (const r of rows) {
                text += `${emojis[c]} ${await getFullName(r.user_id)} - ${r.count}\n`;
                c++;
            }
            await context.editMessage({ message: text, keyboard: getTopMsgKb() });
            return await context.answer();
        }

        // --- МИНЫ ---
        if (payload.cmd === 'mines_set') {
            const { gameId, count } = payload;
            const row = await dbGet("SELECT bet FROM games WHERE game_id = ? AND user_id = ?", [gameId, String(userId)]);
            if (row) {
                const minesArr = [];
                while(minesArr.length < count) { const r = Math.floor(Math.random() * 9) + 1; if (!minesArr.includes(r)) minesArr.push(r); }
                await dbRun("UPDATE games SET mines = ?, opened = '[]', multiplier = 1.0 WHERE game_id = ?", [JSON.stringify(minesArr), gameId]);
                await context.answer(); 
                await vk.api.messages.edit({ peer_id: context.peerId, conversation_message_id: context.conversationMessageId, message: `💣 Мины\nСтавка: ${row.bet}$ | Мин: ${count}\nВыбирай клетку:`, keyboard: getMinesFieldKb(gameId, [], minesArr) });
            }
        }

        if (payload.cmd === 'mines_click') {
            const { gameId, cell } = payload;
            const row = await dbGet("SELECT bet, mines, opened, multiplier FROM games WHERE game_id = ? AND user_id = ?", [gameId, String(userId)]);
            if (row) {
                const mines = JSON.parse(row.mines); const opened = JSON.parse(row.opened);
                if (opened.includes(cell)) return await context.answer();
                opened.push(cell);
                if (mines.includes(cell)) {
                    await updateBalance(userId, -row.bet); await dbRun("DELETE FROM games WHERE game_id = ?", [gameId]);
                    await context.answer({ type: 'show_snackbar', text: '💥 БУМ!' });
                    return await vk.api.messages.edit({ peer_id: context.peerId, conversation_message_id: context.conversationMessageId, message: `💥 Вы подорвались!\nПроигрыш: -${row.bet}$`, keyboard: getMinesFieldKb(gameId, [1,2,3,4,5,6,7,8,9], mines, true) });
                }
                let newMult = 1.0; for (let i = 0; i < opened.length; i++) newMult *= (9 - i) / (9 - mines.length - i);
                newMult = Math.round(newMult * 0.95 * 100) / 100;
                await dbRun("UPDATE games SET opened = ?, multiplier = ? WHERE game_id = ?", [JSON.stringify(opened), newMult, gameId]);
                await context.answer({ type: 'show_snackbar', text: `💎 x${newMult}` });
                await vk.api.messages.edit({ peer_id: context.peerId, conversation_message_id: context.conversationMessageId, message: `💣 Мины\nКоэф: x${newMult}\nВыигрыш: ${Math.floor(row.bet * newMult)}$`, keyboard: getMinesFieldKb(gameId, opened, mines) });
            }
        }

        if (payload.cmd === 'mines_cashout') {
            const { gameId } = payload;
            const row = await dbGet("SELECT bet, multiplier, mines FROM games WHERE game_id = ? AND user_id = ?", [gameId, String(userId)]);
            if (row) {
                const win = Math.floor(row.bet * row.multiplier); await updateBalance(userId, win); await dbRun("DELETE FROM games WHERE game_id = ?", [gameId]);
                await context.answer({ type: 'show_snackbar', text: `💰 Забрано: ${win}$` });
                await vk.api.messages.edit({ peer_id: context.peerId, conversation_message_id: context.conversationMessageId, message: `💰 Вы забрали ${win}$!`, keyboard: "" });
            }
        }

    } catch (e) { console.error(e); }
});

// ===== ЗАПУСК =====
vk.updates.startPolling().then(() => console.log("--- БОТ ЗАПУЩЕН ---")).catch(console.error);
