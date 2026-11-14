const { VK, Keyboard } = require('vk-io');
const sqlite3 = require('sqlite3').verbose();
const fs = require('fs');
const path = require('path');

console.log("=========================================");
console.log("ВЕРСИЯ NODE.JS:", process.version);
console.log("=========================================");

// ===== НАСТРОЙКИ =====
const TOKEN = "vk1.a.KhWSBHlF9P2PScW-7_RjYfo_-nSXdof8v7djx9V2ZBO8fs7hyuI3modscfofRSUOy5CJUZu5DwlRnoZ14j5HIe8bukJK7iPnYr_NqFwIeHjFkh_u0MRDvN07ZZfnbgIe6dZo2QBrihqyOeVgqtzJuI75m4EFMUTb4hicEet1DNBWCke0-eahDyGxEAA01yYYqZHlMSCTOdy7HU7tjcoCR_SNutXQ4Inw7eiMYLxKjws";
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

const gameCooldowns = new Map();
const adminStates = new Map();
const spamCache = new Map();

const BIZ_DATA = {
    'шаурма': { name: '🌯 Шаурма', price: 500000, baseIncome: 2000 },
    'кафе': { name: '☕ Кафе', price: 1500000, baseIncome: 4000 },
    'game zone': { name: '🕹️ Отдел Game Zone', price: 5000000, baseIncome: 6000 },
    'казино': { name: '🎰 Казино', price: 15000000, baseIncome: 10000 },
    'пятерочка': { name: '🏪 24/7 Пятёрочка', price: 50000000, baseIncome: 15000 }
};

const CARS_DATA = {
    'м5 ф90': { name: 'BMW M5 F90', price: 15000000 },
    'м5 ф10': { name: 'BMW M5 F10', price: 8000000 },
    'м3': { name: 'BMW M3 G80', price: 12000000 },
    'мерседес': { name: 'Mercedes-Benz E-Class', price: 10000000 },
    'ауди': { name: 'Audi RS7', price: 18000000 },
    'ламборгини': { name: 'Lamborghini Huracan', price: 35000000 },
    'порше': { name: 'Porsche 911 Turbo', price: 28000000 }
};

async function initDB() {
    await dbRun("CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, balance INTEGER DEFAULT 1000, reputation INTEGER DEFAULT 0, xp INTEGER DEFAULT 0, level INTEGER DEFAULT 1, reg_date TEXT, duel_wins INTEGER DEFAULT 0, bonus_count INTEGER DEFAULT 0)");
    await dbRun("CREATE TABLE IF NOT EXISTS active_duels (msg_id TEXT PRIMARY KEY, challenger TEXT, bet INTEGER, peer_id TEXT)");
    await dbRun("CREATE TABLE IF NOT EXISTS bonus_cd (user_id TEXT PRIMARY KEY, last_used INTEGER)");
    await dbRun("CREATE TABLE IF NOT EXISTS fortune_cd (user_id TEXT PRIMARY KEY, last_used INTEGER)");
    await dbRun("CREATE TABLE IF NOT EXISTS promos (code TEXT PRIMARY KEY, amount INTEGER, limit_count INTEGER, used_by TEXT DEFAULT '')");
    await dbRun("CREATE TABLE IF NOT EXISTS games (game_id TEXT PRIMARY KEY, user_id TEXT, bet INTEGER, mines TEXT, opened TEXT, multiplier REAL, msg_id TEXT, start_time INTEGER)");
    await dbRun("CREATE TABLE IF NOT EXISTS blacklist (user_id TEXT PRIMARY KEY, reason TEXT)");
    await dbRun("CREATE TABLE IF NOT EXISTS chat_messages (peer_id TEXT, user_id TEXT, count INTEGER DEFAULT 0, PRIMARY KEY (peer_id, user_id))");
    await dbRun("CREATE TABLE IF NOT EXISTS businesses (user_id TEXT PRIMARY KEY, biz_name TEXT, level INTEGER DEFAULT 1, balance INTEGER DEFAULT 0, last_income INTEGER, last_withdraw INTEGER DEFAULT 0)");
    await dbRun("CREATE TABLE IF NOT EXISTS rep_limits (user_id TEXT PRIMARY KEY, count INTEGER DEFAULT 0, last_reset INTEGER)");
    await dbRun("CREATE TABLE IF NOT EXISTS work_cd (user_id TEXT PRIMARY KEY, count INTEGER DEFAULT 0, last_reset INTEGER)");
    await dbRun("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)");

    try { await dbRun("ALTER TABLE users ADD COLUMN reputation INTEGER DEFAULT 0"); } catch(e) {}
    try { await dbRun("ALTER TABLE users ADD COLUMN xp INTEGER DEFAULT 0"); } catch(e) {}
    try { await dbRun("ALTER TABLE users ADD COLUMN level INTEGER DEFAULT 1"); } catch(e) {}
    try { await dbRun("ALTER TABLE users ADD COLUMN reg_date TEXT"); } catch(e) {}
    try { await dbRun("ALTER TABLE users ADD COLUMN duel_wins INTEGER DEFAULT 0"); } catch(e) {}
    try { await dbRun("ALTER TABLE users ADD COLUMN bonus_count INTEGER DEFAULT 0"); } catch(e) {}
    try { await dbRun("ALTER TABLE businesses ADD COLUMN last_withdraw INTEGER DEFAULT 0"); } catch(e) {}
    try { await dbRun("ALTER TABLE games ADD COLUMN start_time INTEGER"); } catch(e) {}
    try { await dbRun("ALTER TABLE users ADD COLUMN car TEXT DEFAULT NULL"); } catch(e) {}
    
    await dbRun("INSERT OR IGNORE INTO settings (key, value) VALUES ('antispam_enabled', '0')");
    await dbRun("INSERT OR IGNORE INTO settings (key, value) VALUES ('antispam_limit', '5')");
    await dbRun("INSERT OR IGNORE INTO settings (key, value) VALUES ('antispam_time', '60')");
    await dbRun("INSERT OR IGNORE INTO settings (key, value) VALUES ('antispam_mute', '10')");
}
initDB();

function parseAmount(str) {
    if (!str) return 0;
    str = String(str).toLowerCase().replace(/\s/g, '');
    if (str.endsWith('всё') || str.endsWith('все') || str.endsWith('вб')) return 'ALL'; 
    let mult = 1;
    if (str.endsWith('ккк') || str.endsWith('kkk')) { mult = 1000000000; str = str.slice(0, -3); }
    else if (str.endsWith('кк') || str.endsWith('kk')) { mult = 1000000; str = str.slice(0, -2); }
    else if (str.endsWith('к') || str.endsWith('k')) { mult = 1000; str = str.slice(0, -1); }
    else if (str.endsWith('м') || str.endsWith('m')) { mult = 1000000; str = str.slice(0, -1); }
    let num = parseFloat(str.replace(',', '.'));
    if (isNaN(num)) return 0;
    return Math.floor(num * mult);
}

async function getBalance(userId) {
    const row = await dbGet("SELECT balance FROM users WHERE user_id = ?", [String(userId)]);
    if (!row) { await dbRun("INSERT INTO users (user_id, balance) VALUES (?, 1000)", [String(userId)]); return 1000; }
    let bal = Number(row.balance);
    if (isNaN(bal) || !isFinite(bal)) { await dbRun("UPDATE users SET balance = 0 WHERE user_id = ?", [String(userId)]); return 0; }
    return bal;
}
async function updateBalance(userId, amount) {
    const bal = await getBalance(userId);
    let amt = Number(amount);
    if (isNaN(amt) || !isFinite(amt)) amt = 0;
    await dbRun("UPDATE users SET balance = ? WHERE user_id = ?", [Math.floor(Number(bal) + amt), String(userId)]);
}
async function getReputation(userId) { const row = await dbGet("SELECT reputation FROM users WHERE user_id = ?", [String(userId)]); return row ? (Number(row.reputation) || 0) : 0; }
async function updateReputation(userId, amount) { await dbRun("UPDATE users SET reputation = ? WHERE user_id = ?", [(await getReputation(userId)) + amount, String(userId)]); }
async function getFullName(userId) { try { const [user] = await vk.api.users.get({ user_ids: userId }); return `[id${userId}|${user.first_name} ${user.last_name || ''}]`; } catch { return `[id${userId}|Игрок]`; } }
function formatMoney(num) { let n = Number(num); if (isNaN(n) || !isFinite(n)) n = 0; return n.toLocaleString('ru-RU'); }

async function getTargetAndReason(message, cmdName) {
    let targetId = null; let text = message.text || ''; let reason = text.replace(new RegExp(`^\\/?${cmdName}\\s*`, 'i'), '');
    if (message.hasReplyMessage) { targetId = message.replyMessage.senderId; }
    else {
        const idMatch = reason.match(/\[id(\d+)\|[^\]]+\]/i);
        if (idMatch) { targetId = parseInt(idMatch[1]); reason = reason.replace(idMatch[0], ''); }
        else {
            const atIdMatch = reason.match(/@id(\d+)/i);
            if (atIdMatch) { targetId = parseInt(atIdMatch[1]); reason = reason.replace(atIdMatch[0], ''); }
            else {
                const urlMatch = reason.match(/(?:https?:\/\/)?(?:vk\.com|vk\.ru)\/([a-zA-Z0-9._]+)/i);
                if (urlMatch) { try { const res = await vk.api.utils.resolveScreenName({ screen_name: urlMatch[1] }); if (res.type === 'user' || res.type === 'group') targetId = res.object_id; } catch (e) {} reason = reason.replace(urlMatch[0], ''); }
                else {
                    const mentionMatch = reason.match(/@([a-zA-Z0-9._]+)/i);
                    if (mentionMatch) { try { const res = await vk.api.utils.resolveScreenName({ screen_name: mentionMatch[1] }); if (res.type === 'user') targetId = res.object_id; } catch (e) {} reason = reason.replace(mentionMatch[0], ''); }
                }
            }
        }
    }
    reason = reason.replace(/[\[\]]/g, '').replace(/"/g, '').trim();
    if (!reason) reason = "Причина не указана";
    return { targetId, reason };
}

function getMinesGameUI(gameId, bet, minesCount, minesArr, opened, isLoss = false, hitCell = null, name = "", balance = 0, timeLeft = 60) {
    const totalSafe = 9 - minesCount; const currentOpened = opened.length;
    let currentMult = 1.0;
    for (let i = 0; i < currentOpened; i++) currentMult *= (9 - i) / (9 - minesCount - i);
    currentMult = Math.round(currentMult * 0.95 * 100) / 100;
    const currentMoney = Math.floor(bet * currentMult);
    let nextMult = 1.0;
    if (currentOpened < totalSafe) { for (let i = 0; i <= currentOpened; i++) nextMult *= (9 - i) / (9 - minesCount - i); nextMult = Math.round(nextMult * 0.95 * 100) / 100; }
    const nextMoney = Math.floor(bet * nextMult); const chance = Math.floor(((9 - minesCount - currentOpened) / (9 - currentOpened)) * 100);
    let progressBar = "🟩".repeat(currentOpened) + "⬜".repeat(totalSafe - currentOpened);
    if (isLoss) {
        const lostMoney = currentMoney;
        return { text: `💥 БАБАХ! ПОРАЖЕНИЕ\n────────────────────\n👤 ${name} наступил(а) на мину!\n💣 Мин на поле: ${minesCount}\n✅ Успел(а) открыть: ${currentOpened}\n\n📉 Потеряно: -${bet} 💰\n😢 Не забрал(а): ${lostMoney} 💰 (x${currentMult})\n💳 Баланс: ${formatMoney(balance)} 💰\n\n💬 Бывает. Следующая будет твоей 🍀`, kb: buildMinesKb(gameId, opened, minesArr, true, hitCell) };
    } else {
        const randomPhrases = ["Выбирай клетку! Первый ход — самый волнующий 😈", "Чисто! Сапёр бы гордился 👏", "Ещё немного, и можно забирать 💸", "Осторожно, мины рядом... 💣", "Фортуна улыбается тебе 😉"];
        const phrase = currentOpened === 0 ? randomPhrases[0] : randomPhrases[Math.floor(Math.random() * (randomPhrases.length - 1)) + 1];
        return { text: `💣 МИНЫ\n────────────────────\n👤 ${name}\n💵 Ставка: ${bet} | 💣 Мин: ${minesCount}\n\n${progressBar} ${currentOpened}/${totalSafe}\n📈 Сейчас: x${currentMult.toFixed(2)} → ${currentMoney} 💰\n🎯 Следующая: x${nextMult.toFixed(2)} → ${nextMoney} 💰\n🍀 Шанс безопасной клетки: ${chance}%\n⏱ Осталось: ${timeLeft} сек.\n\n💬 ${phrase}`, kb: buildMinesKb(gameId, opened, minesArr, false, null, currentMoney) };
    }
}

function buildMinesKb(gameId, opened, mines = [], isGameOver = false, hitCell = null, currentMoney = 0) {
    const kb = Keyboard.builder().inline();
    for (let i = 1; i <= 9; i++) {
        if (isGameOver) {
            if (i === hitCell) kb.callbackButton({ label: '💥', payload: { cmd: 'none' }, color: Keyboard.NEGATIVE_COLOR });
            else if (mines.includes(i)) kb.callbackButton({ label: '💣', payload: { cmd: 'none' }, color: Keyboard.NEGATIVE_COLOR });
            else if (opened.includes(i)) kb.callbackButton({ label: '✅', payload: { cmd: 'none' }, color: Keyboard.POSITIVE_COLOR });
            else kb.callbackButton({ label: '⬜', payload: { cmd: 'none' }, color: Keyboard.SECONDARY_COLOR });
        } else {
            if (opened.includes(i)) kb.callbackButton({ label: '✅', payload: { cmd: 'none' }, color: Keyboard.POSITIVE_COLOR });
            else kb.callbackButton({ label: '❓', payload: { cmd: 'mines_click', gameId: String(gameId), cell: String(i) }, color: Keyboard.SECONDARY_COLOR });
        }
        if (i % 3 === 0) kb.row();
    }
    if (!isGameOver && currentMoney > 0 && opened.length > 0) kb.callbackButton({ label: `💰 Забрать ${currentMoney}`, payload: { cmd: 'mines_cashout', gameId: String(gameId) }, color: Keyboard.SECONDARY_COLOR });
    return kb.toString();
}

const mainKb = Keyboard.builder()
    .textButton({ label: '💼 Работа', payload: 'work', color: Keyboard.POSITIVE_COLOR })
    .textButton({ label: '🎰 Рулетка', payload: 'roulette', color: Keyboard.PRIMARY_COLOR })
    .row()
    .textButton({ label: '👤 Профиль', payload: 'profile', color: Keyboard.SECONDARY_COLOR })
    .textButton({ label: '🏆 Топ', payload: 'top', color: Keyboard.SECONDARY_COLOR });

const getWorkKb = () => Keyboard.builder().inline().callbackButton({ label: '🎣 Рыбалка', payload: { cmd: 'work_do', type: 'Рыбалка' }, color: Keyboard.POSITIVE_COLOR }).callbackButton({ label: '🚕 Такси', payload: { cmd: 'work_do', type: 'Такси' }, color: Keyboard.POSITIVE_COLOR }).callbackButton({ label: '🔫 Охота', payload: { cmd: 'work_do', type: 'Охота' }, color: Keyboard.POSITIVE_COLOR }).toString();
const getCasinoKb = () => Keyboard.builder().inline().callbackButton({ label: 'Рулетка', payload: { cmd: 'casino_info', game: 'roulette' }, color: Keyboard.SECONDARY_COLOR }).callbackButton({ label: 'Краш', payload: { cmd: 'casino_info', game: 'crash' }, color: Keyboard.SECONDARY_COLOR }).row().callbackButton({ label: 'Монетка', payload: { cmd: 'casino_info', game: 'coin' }, color: Keyboard.SECONDARY_COLOR }).callbackButton({ label: 'Стакан', payload: { cmd: 'casino_info', game: 'glass' }, color: Keyboard.SECONDARY_COLOR }).row().callbackButton({ label: 'Кубик', payload: { cmd: 'casino_info', game: 'dice' }, color: Keyboard.SECONDARY_COLOR }).callbackButton({ label: 'Автомат', payload: { cmd: 'casino_info', game: 'slot' }, color: Keyboard.SECONDARY_COLOR }).row().callbackButton({ label: 'Блэкджек', payload: { cmd: 'casino_info', game: 'blackjack' }, color: Keyboard.NEGATIVE_COLOR }).callbackButton({ label: 'Дрим', payload: { cmd: 'casino_info', game: 'dream' }, color: Keyboard.NEGATIVE_COLOR }).toString();
const getHelpKb = () => Keyboard.builder().inline().callbackButton({ label: '🎰 Игры', payload: { cmd: 'help_menu', section: 'games' }, color: Keyboard.PRIMARY_COLOR }).callbackButton({ label: '💼 Экономика', payload: { cmd: 'help_menu', section: 'eco' }, color: Keyboard.SECONDARY_COLOR }).row().callbackButton({ label: '👤 Профиль', payload: { cmd: 'help_menu', section: 'profile' }, color: Keyboard.SECONDARY_COLOR }).toString();
const getHelpBackKb = () => Keyboard.builder().inline().callbackButton({ label: '🔙 Назад', payload: { cmd: 'help_start' }, color: Keyboard.SECONDARY_COLOR }).toString();
const getSettingsKb = async (enabled, limit, time, mute) => {
    const kb = Keyboard.builder().inline();
    kb.callbackButton({ label: '🟢 Включить', payload: { cmd: 'settings_toggle', state: '1' }, color: enabled === '1' ? Keyboard.POSITIVE_COLOR : Keyboard.SECONDARY_COLOR });
    kb.callbackButton({ label: '🔴 Выключить', payload: { cmd: 'settings_toggle', state: '0' }, color: enabled === '0' ? Keyboard.NEGATIVE_COLOR : Keyboard.SECONDARY_COLOR });
    kb.row().callbackButton({ label: `Лимит: ${limit}`, payload: { cmd: 'settings_edit', field: 'limit' }, color: Keyboard.SECONDARY_COLOR }).callbackButton({ label: `Время (сек): ${time}`, payload: { cmd: 'settings_edit', field: 'time' }, color: Keyboard.SECONDARY_COLOR }).row().callbackButton({ label: `Мут (мин): ${mute}`, payload: { cmd: 'settings_edit', field: 'mute' }, color: Keyboard.SECONDARY_COLOR });
    return kb.toString();
};
const getDuelKb = (duelId) => Keyboard.builder().inline().callbackButton({ label: '⚔️ Сразиться', payload: { cmd: 'duel_accept', duel_id: duelId }, color: Keyboard.POSITIVE_COLOR }).toString();
const getMinesCountKb = (gameId) => {
    const kb = Keyboard.builder().inline();
    let count = 0;
    for (let i = 2; i <= 8; i++) { kb.callbackButton({ label: `${i} 💣`, payload: { cmd: 'mines_set', gameId: String(gameId), count: String(i) }, color: Keyboard.SECONDARY_COLOR }); count++; if (count % 4 === 0 && i !== 8) kb.row(); }
    return kb.toString();
};
const getTopKb = (authorId, type = 'coins', scope = 'chat', repType = 'pos') => {
    const kb = Keyboard.builder().inline();
    kb.callbackButton({ label: '💰 Моне...', payload: { cmd: 'top_menu', type: 'coins', scope, repType, author: authorId }, color: type === 'coins' ? Keyboard.PRIMARY_COLOR : Keyboard.SECONDARY_COLOR }).callbackButton({ label: '📊 Уров...', payload: { cmd: 'top_menu', type: 'level', scope, repType, author: authorId }, color: type === 'level' ? Keyboard.PRIMARY_COLOR : Keyboard.SECONDARY_COLOR }).callbackButton({ label: '⭐ Репу...', payload: { cmd: 'top_menu', type: 'rep', scope, repType, author: authorId }, color: type === 'rep' ? Keyboard.PRIMARY_COLOR : Keyboard.SECONDARY_COLOR }).row();
    kb.callbackButton({ label: '⚔️ Дуэли', payload: { cmd: 'top_menu', type: 'duels', scope, repType, author: authorId }, color: type === 'duels' ? Keyboard.PRIMARY_COLOR : Keyboard.SECONDARY_COLOR }).callbackButton({ label: '🎁 Бонус', payload: { cmd: 'top_menu', type: 'bonus', scope, repType, author: authorId }, color: type === 'bonus' ? Keyboard.PRIMARY_COLOR : Keyboard.SECONDARY_COLOR }).row();
    if (type === 'rep') { kb.callbackButton({ label: '➕ Положит.', payload: { cmd: 'top_menu', type: 'rep', scope, repType: 'pos', author: authorId }, color: repType === 'pos' ? Keyboard.POSITIVE_COLOR : Keyboard.SECONDARY_COLOR }).callbackButton({ label: '➖ Отрицат.', payload: { cmd: 'top_menu', type: 'rep', scope, repType: 'neg', author: authorId }, color: repType === 'neg' ? Keyboard.NEGATIVE_COLOR : Keyboard.SECONDARY_COLOR }).row(); }
    kb.callbackButton({ label: '🌍 Общее', payload: { cmd: 'top_menu', type, scope: 'global', repType, author: authorId }, color: scope === 'global' ? Keyboard.PRIMARY_COLOR : Keyboard.SECONDARY_COLOR }).callbackButton({ label: '💬 В беседе', payload: { cmd: 'top_menu', type, scope: 'chat', repType, author: authorId }, color: scope === 'chat' ? Keyboard.PRIMARY_COLOR : Keyboard.SECONDARY_COLOR }).row().callbackButton({ label: '🔙 Назад', payload: { cmd: 'top_back', author: authorId }, color: Keyboard.SECONDARY_COLOR });
    return kb.toString();
};
const getBizKb = (authorId) => Keyboard.builder().inline().callbackButton({ label: 'Повысить уровень', payload: { cmd: 'biz_upgrade', author: authorId }, color: Keyboard.SECONDARY_COLOR }).toString();

vk.updates.on('chat_invite_user', async (context) => {
    if (String(context.memberId) === String(-GROUP_ID)) {
        const actKb = Keyboard.builder().inline().callbackButton({ label: 'Активировать', payload: { cmd: 'activate_bot' }, color: Keyboard.POSITIVE_COLOR }).callbackButton({ label: 'Не активировать', payload: { cmd: 'decline_bot' }, color: Keyboard.NEGATIVE_COLOR });
        try { await vk.api.messages.send({ peer_id: context.peerId, message: "Привет! Я Официальный бот Game Zone. Для того чтобы я начал работать, выдайте мне права администратора и напишите /start. После этого напишите /help для ознакомления с командами.", keyboard: actKb.toString(), random_id: Math.floor(Math.random() * 1000000000), group_id: GROUP_ID, disable_mentions: 1 }); } catch (err) {}
    }
});

vk.updates.on('message_new', async (message) => {
    if (message.isOutbox) return; if (message.senderId < 0) return;
    try {
        const text = message.text ? message.text.trim().toLowerCase() : ''; if (!text) return;
        const userId = message.senderId; const peerId = message.peerId; const isLs = peerId === userId;
        const cleanText = text.replace(/\//g, '').trim(); const parts = cleanText.split(/\s+/); const cmdWord = parts[0];

        // --- ЛОГИКА АНТИСПАМА (МУТ) ---
        if (message.isChat && userId !== ADMIN_ID) {
            const spamEnabled = await dbGet("SELECT value FROM settings WHERE key = 'antispam_enabled'");
            if (spamEnabled && spamEnabled.value === '1') {
                const limit = Number((await dbGet("SELECT value FROM settings WHERE key = 'antispam_limit'"))?.value || 5);
                const timeSec = Number((await dbGet("SELECT value FROM settings WHERE key = 'antispam_time'"))?.value || 60);
                const muteMin = Number((await dbGet("SELECT value FROM settings WHERE key = 'antispam_mute'"))?.value || 10);
                const now = Date.now(); const cacheKey = `${peerId}_${userId}`; let spamData = spamCache.get(cacheKey) || { count: 0, lastReset: now, isMuted: false, muteEndTime: 0 };

                if (spamData.isMuted && now < spamData.muteEndTime) {
                    try { 
                        // Правильное удаление для беседы: peer_id, cmids, group_id
                        await vk.api.messages.delete({ peer_id: peerId, cmids: [message.conversationMessageId], delete_for_all: 1, group_id: GROUP_ID }); 
                    } catch (e) { 
                        // Если ВК запретил удалять, молчим
                    }
                    return;
                } else if (spamData.isMuted && now >= spamData.muteEndTime) {
                    spamData.isMuted = false;
                }

                if (now - spamData.lastReset >= timeSec * 1000) { spamData.count = 0; spamData.lastReset = now; }
                spamData.count++; spamCache.set(cacheKey, spamData);

                if (spamData.count >= limit && !spamData.isMuted) {
                    spamData.isMuted = true; spamData.muteEndTime = now + (muteMin * 60 * 1000); spamCache.set(cacheKey, spamData);
                    try {
                        await vk.api.messages.changeConversationMemberRestrictions({ group_id: GROUP_ID, peer_id: peerId, member_id: userId, action: 'ro', for: muteMin * 60 });
                        await message.reply(`🚫 [id${userId}|Игрок] получил блокировку чата на ${muteMin} минут за нарушение антиспама.`);
                        spamData.count = 0; spamCache.set(cacheKey, spamData);
                        try { await vk.api.messages.delete({ peer_id: peerId, cmids: [message.conversationMessageId], delete_for_all: 1, group_id: GROUP_ID }); } catch(e) {}
                    } catch(e) {
                        console.error("Не удалось выдать мут:", e.message);
                        spamData.isMuted = false; spamCache.set(cacheKey, spamData);
                    }
                }
            }
        }

        if (userId === ADMIN_ID && adminStates.has(userId)) {
            const state = adminStates.get(userId); const val = parseFloat(cleanText);
            if (!isNaN(val) && val > 0) {
                await dbRun("UPDATE settings SET value = ? WHERE key = ?", [String(val), state]); adminStates.delete(userId);
                const enabled = (await dbGet("SELECT value FROM settings WHERE key = 'antispam_enabled'")).value; const limit = (await dbGet("SELECT value FROM settings WHERE key = 'antispam_limit'")).value; const time = (await dbGet("SELECT value FROM settings WHERE key = 'antispam_time'")).value; const mute = (await dbGet("SELECT value FROM settings WHERE key = 'antispam_mute'")).value;
                return await message.reply(`✅ Настройки сохранены!\n\n⚙️ Статус: ${enabled === '1' ? "🟢 Включен" : "🔴 Выключен"}`, { keyboard: await getSettingsKb(enabled, limit, time, mute) });
            } else return await message.reply("❌ Введите корректное число больше 0.");
        }

        const validCmds = ['стакан', 'кубик', 'монетка', 'дрим', 'краш', 'рулетка', 'рул', 'автомат', 'блэкджек', 'мины', 'топ', 'профиль', 'баланс', 'бизнес', 'машины', 'работа', 'бонус', 'фортуна', 'казино', 'help', 'помощь', 'start', 'начать', 'transfer', 'перевод', 'duel', 'вывести', 'мойбизнес', 'закрыть', 'rep', 'реп', 'промолист', 'promo', 'купить', 'купитьбиз', 'чсб', 'разчсб', 'kick', 'выдать', 'обнулить', 'создать', 'cp', 'ping', 'пинг', 'убрать', 'настройки', 'unmute'];
        const isMainButton = text.includes('работа') || text.includes('рулетка') || text.includes('профиль') || text.includes('топ');
        if (!text.startsWith('/') && !validCmds.includes(cmdWord) && !isMainButton) return;

        let userRow = await dbGet("SELECT xp, level, reg_date FROM users WHERE user_id = ?", [String(userId)]);
        if (!userRow) { await dbRun("INSERT INTO users (user_id, balance, reg_date) VALUES (?, 1000, ?)", [String(userId), new Date().toLocaleDateString('ru-RU')]); }
        else {
            let newXp = (Number(userRow.xp) || 0) + 40; let newLvl = Number(userRow.level) || 1;
            while (newXp >= newLvl * 500) { newXp -= newLvl * 500; newLvl++; }
            await dbRun("UPDATE users SET xp = ?, level = ? WHERE user_id = ?", [newXp, newLvl, String(userId)]);
        }

        if (message.isChat) {
            const existing = await dbGet("SELECT count FROM chat_messages WHERE peer_id = ? AND user_id = ?", [String(peerId), String(userId)]);
            if (existing) await dbRun("UPDATE chat_messages SET count = count + 1 WHERE peer_id = ? AND user_id = ?", [String(peerId), String(userId)]);
            else await dbRun("INSERT INTO chat_messages (peer_id, user_id, count) VALUES (?, ?, 1)", [String(peerId), String(userId)]);
        }

        if (text.startsWith('/') && userId !== ADMIN_ID) {
            const isBlacklisted = await dbGet("SELECT reason FROM blacklist WHERE user_id = ?", [String(userId)]);
            if (isBlacklisted) return await message.reply(`🚫 Доступ запрещен!\n👤 ID: ${userId}\n📌 Причина: ${isBlacklisted.reason}`, { disable_mentions: 1 });
        }

        const balance = await getBalance(userId); const rep = await getReputation(userId);
        const replyParams = (kb = undefined) => { const p = { disable_mentions: 1 }; if (kb) p.keyboard = kb; return p; };

        if (text.includes('начать') || text.includes('start')) {
            if (message.isChat) {
                try {
                    const members = await vk.api.messages.getConversationMembers({ peer_id: peerId });
                    const admin = members.items.find(m => m.member_id === userId && (m.is_admin || m.is_owner));
                    if (!admin && userId !== ADMIN_ID) return await message.reply("⚠️ Ошибка! Вы не администратор беседы.", replyParams());
                    return await message.reply("✅ Бот успешно активирован! Напишите /help.", replyParams());
                } catch(e) { return await message.reply("⚠️ Ошибка! Убедитесь, что я администратор беседы.", replyParams()); }
            } else return await message.reply("👋 Привет! Выбирай действие на клавиатуре или напиши /help.", replyParams(mainKb));
        }

        if (text.includes('help') || text.includes('помощь') || text.includes('команды')) return await message.reply("📖 Выберите раздел:", replyParams(getHelpKb()));
        if (cleanText === 'ping' || cleanText === 'пинг') {
            const start = Date.now(); try { await vk.api.users.get({ user_ids: userId }); } catch (e) {}
            const ping = Date.now() - start; let status = "🟢 Отлично"; if (ping > 150) status = "🟡 Нормально"; if (ping > 300) status = "🔴 Плохо";
            return await message.reply(`🏓 Понг!\n⚡ Пинг: ${ping} мс\n📊 Статус: ${status}`, replyParams());
        }

        if (cleanText.includes('профиль') || cleanText.includes('баланс')) {
            const uInfo = await dbGet("SELECT xp, level, reg_date, car FROM users WHERE user_id = ?", [String(userId)]);
            return await message.reply(`🏠 Профиль ${await getFullName(userId)}\n\n💵 Баланс: ${formatMoney(balance)}$\n⭐ Репутация: ${rep}\n📊 Уровень: ${uInfo.level || 1} (${uInfo.xp || 0}/${(uInfo.level || 1) * 500} XP)\n🚗 Авто: ${uInfo.car || "Нет"}\n📅 Регистрация: ${uInfo.reg_date || "Неизвестно"}\n🆔 ID: ${userId}`, replyParams(isLs ? mainKb : undefined));
        }

        if (cleanText === 'машины') {
            let txt = "🚗 Доступные машины:\n\n"; for (const [key, data] of Object.entries(CARS_DATA)) txt += `${data.name} — ${formatMoney(data.price)}$\n`;
            txt += "\n🛒 Купить: /купить машина [Название]"; return await message.reply(txt, replyParams());
        }
        if (cleanText.startsWith('купить машина')) {
            const args = message.text.split(' '); args.shift(); args.shift(); const query = args.join(' ').toLowerCase().trim();
            if (!query) return await message.reply("❌ Укажите название машины.", replyParams());
            let selectedCar = null; for (const [key, data] of Object.entries(CARS_DATA)) if (key.includes(query) || data.name.toLowerCase().includes(query)) { selectedCar = data; break; }
            if (!selectedCar) return await message.reply("❌ Такой машины нет. Список: /машины", replyParams());
            const userCarRow = await dbGet("SELECT car FROM users WHERE user_id = ?", [String(userId)]);
            if (userCarRow && userCarRow.car) return await message.reply(`❌ У вас уже есть машина (${userCarRow.car}).`, replyParams());
            if (balance < selectedCar.price) return await message.reply(`❌ Не хватает денег! Нужно ${formatMoney(selectedCar.price)}$`, replyParams());
            await updateBalance(userId, -selectedCar.price); await dbRun("UPDATE users SET car = ? WHERE user_id = ?", [selectedCar.name, String(userId)]);
            return await message.reply(`🎉 Поздравляем! Вы купили ${selectedCar.name} за ${formatMoney(selectedCar.price)}$.`, replyParams());
        }

        if (cleanText === 'казино') return await message.reply("🎰 Игры:", replyParams(getCasinoKb()));
        if (cleanText.includes('топ') || cleanText === 'top') {
            const rows = await dbAll("SELECT user_id, count FROM chat_messages WHERE peer_id = ? ORDER BY count DESC LIMIT 10", [String(peerId)]);
            let topText = "⭐ ТОП 10 ПО СООБЩЕНИЯМ\n\n";
            if (rows.length > 0) {
                const userIds = rows.map(r => r.user_id); let usersInfo = []; try { usersInfo = await vk.api.users.get({ user_ids: userIds.join(','), fields: 'deactivated' }); } catch (e) {}
                let count = 0; const emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"];
                for (const r of rows) { const uInfo = usersInfo.find(u => u.id == r.user_id); if (uInfo && !uInfo.deactivated) { topText += `${emojis[count]} [id${uInfo.id}|${uInfo.first_name} ${uInfo.last_name || ''}] - ${r.count} сообщений\n`; count++; } }
            } else topText += "В этой беседе еще никто не писал.";
            return await message.reply(topText, replyParams(getTopKb(userId, 'coins', 'chat')));
        }

        if (cleanText === 'бизнес') {
            let bizText = "🏢 Доступные бизнесы:\n\n"; for (const [key, data] of Object.entries(BIZ_DATA)) bizText += `${data.name} — ${formatMoney(data.price)}$ (Доход: ~${formatMoney(data.baseIncome)}$/3мин)\n`;
            bizText += "\nЧтобы купить, напишите /купитьбиз [Название]"; return await message.reply(bizText, replyParams());
        }
        if (cleanText.startsWith('купитьбиз')) {
            const args = message.text.split(' '); args.shift(); const bizQuery = args.join(' ').toLowerCase().trim();
            if (!bizQuery) return await message.reply("❌ Укажите название бизнеса.", replyParams());
            const existing = await dbGet("SELECT biz_name FROM businesses WHERE user_id = ?", [String(userId)]);
            if (existing) return await message.reply("❌ У вас уже есть бизнес. Сначала закройте текущий (/закрыть бизнес).", replyParams());
            let selectedBiz = null; for (const [key, data] of Object.entries(BIZ_DATA)) if (key.includes(bizQuery) || data.name.toLowerCase().includes(bizQuery)) { selectedBiz = data; break; }
            if (!selectedBiz) return await message.reply("❌ Такого бизнеса нет. Список: /бизнес", replyParams());
            if (balance < selectedBiz.price) return await message.reply(`❌ Не хватает денег! Нужно ${formatMoney(selectedBiz.price)}$`, replyParams());
            await updateBalance(userId, -selectedBiz.price); await dbRun("INSERT INTO businesses (user_id, biz_name, level, balance, last_income, last_withdraw) VALUES (?, ?, 1, 0, ?, 0)", [String(userId), selectedBiz.name, Date.now()]);
            return await message.reply(`🎉 Вы успешно купили ${selectedBiz.name} за ${formatMoney(selectedBiz.price)}$.`, replyParams());
        }

        if (cleanText === 'мойбизнес') {
            const biz = await dbGet("SELECT * FROM businesses WHERE user_id = ?", [String(userId)]); if (!biz) return await message.reply("❌ У вас нет бизнеса. Купите его: /бизнес", replyParams());
            const bizData = Object.values(BIZ_DATA).find(b => b.name === biz.biz_name) || { name: biz.biz_name, baseIncome: 1000 }; const timePassed = Date.now() - biz.last_income; const earned = Math.floor(timePassed * ((bizData.baseIncome * biz.level) / 180000)); const totalBalance = Number(biz.balance) + earned;
            const nextLevelCost = (Number(biz.level) === 1 ? 2000000 : Number(biz.level) === 2 ? 5000000 : Number(biz.level) * 5000000);
            return await message.reply(`🏢 Бизнес ${await getFullName(userId)}\n${biz.biz_name}\n\n💪 Уровень: ${biz.level}/5\n🐱 ${formatMoney(bizData.baseIncome * biz.level * 20)}$/час\n💸 На балансе: ${formatMoney(totalBalance)}$\n\nПовышение: ${formatMoney(nextLevelCost)}$\n\n👉 Для вывода напишите /вывести`, replyParams(getBizKb(userId)));
        }

        if (cleanText === 'вывести') {
            const biz = await dbGet("SELECT * FROM businesses WHERE user_id = ?", [String(userId)]); if (!biz) return await message.reply("❌ У вас нет бизнеса.", replyParams());
            const now = Date.now(); const lastWithdraw = Number(biz.last_withdraw) || 0; const cd = 2 * 60 * 60 * 1000;
            if (now - lastWithdraw < cd) { const remaining = cd - (now - lastWithdraw); const h = Math.floor(remaining / 3600000); const m = Math.floor((remaining % 3600000) / 60000); return await message.reply(`⏳ Вывод доступен раз в 2 часа. Ждите: ${h} ч. ${m} мин.`, replyParams()); }
            const bizData = Object.values(BIZ_DATA).find(b => b.name === biz.biz_name) || { name: biz.biz_name, baseIncome: 1000 }; const timePassed = now - biz.last_income; const earned = Math.floor(timePassed * ((bizData.baseIncome * biz.level) / 180000)); const totalBalance = Number(biz.balance) + earned;
            if (totalBalance <= 0) return await message.reply("❌ Нет денег на балансе бизнеса.", replyParams());
            await updateBalance(userId, totalBalance); await dbRun("UPDATE businesses SET balance = 0, last_income = ?, last_withdraw = ? WHERE user_id = ?", [now, now, String(userId)]);
            return await message.reply(`💸 Вы вывели ${formatMoney(totalBalance)}$! Следующий вывод через 2 часа.`, replyParams());
        }

        if (cleanText === 'закрыть бизнес' || cleanText === 'закрытьбизнес') {
            const biz = await dbGet("SELECT biz_name FROM businesses WHERE user_id = ?", [String(userId)]); if (!biz) return await message.reply("❌ У вас нет бизнеса.", replyParams());
            await dbRun("DELETE FROM businesses WHERE user_id = ?", [String(userId)]); await updateBalance(userId, 10000000);
            return await message.reply("💀 Вы закрыли бизнес и получили 10,000,000$ компенсации.", replyParams());
        }

        if (text === '/rep' || text === 'реп') return await message.reply("🔔 Используйте /rep + или /rep - (ответом на сообщение).\n(3 раза в сутки)", replyParams());
        if (text.startsWith('/rep +') || text.startsWith('/rep -')) {
            const isPlus = text.startsWith('/rep +'); let targetId = null;
            if (message.hasReplyMessage) targetId = message.replyMessage.senderId;
            else {
                const targetStr = text.replace('/rep +', '').replace('/rep -', '').trim(); const mentionMatch = targetStr.match(/@([a-zA-Z0-9._]+)/) || targetStr.match(/\[id(\d+)\|/);
                if (mentionMatch) { if(mentionMatch[1].match(/^\d+$/)) targetId = parseInt(mentionMatch[1]); else { try { const res = await vk.api.utils.resolveScreenName({ screen_name: mentionMatch[1] }); if (res.type === 'user') targetId = res.object_id; } catch (e) {} } }
            }
            if (!targetId) return await message.reply("⚠️ Укажите пользователя через @ или ответом.", replyParams());
            if (targetId === userId) return await message.reply("❌ Нельзя изменить репутацию себе!", replyParams());
            const now = Date.now(); const repRow = await dbGet("SELECT count, last_reset FROM rep_limits WHERE user_id = ?", [String(userId)]); let repCount = 0; let repReset = 0;
            if (repRow) { repCount = Number(repRow.count); repReset = Number(repRow.last_reset); }
            if (now - repReset >= 86400000) { repCount = 0; repReset = now; }
            if (repCount >= 3) { const remainingMs = 86400000 - (now - repReset); const hours = Math.floor(remainingMs / 3600000); const minutes = Math.floor((remainingMs % 3600000) / 60000); return await message.reply(`⏳ Лимит (3/сутки). Ждите ${hours} ч. ${minutes} мин.`, replyParams()); }
            repCount++; await dbRun("REPLACE INTO rep_limits (user_id, count, last_reset) VALUES (?, ?, ?)", [String(userId), repCount, repReset]);
            if (isPlus) { await updateReputation(targetId, 1); return await message.reply(`🟢 ${await getFullName(userId)} повысил репутацию ${await getFullName(targetId)} (теперь ${await getReputation(targetId)}).\n📅 Осталось: ${3 - repCount}/3`, replyParams()); }
            else { await updateReputation(targetId, -1); return await message.reply(`🔴 ${await getFullName(userId)} понизил репутацию ${await getFullName(targetId)} (теперь ${await getReputation(targetId)}).\n📅 Осталось: ${3 - repCount}/3`, replyParams()); }
        }

        if (text.includes('работа')) return await message.reply("💼 Выберите работу:", replyParams(getWorkKb()));

        const gameCmds = ['рулетка', 'рул', 'краш', 'монетка', 'стакан', 'кубик', 'автомат', 'блэкджек', 'дрим', 'мины', 'фортуна'];
        if (gameCmds.some(cmd => cleanText.startsWith(cmd))) {
            const lastPlayed = gameCooldowns.get(userId) || 0;
            if (Date.now() - lastPlayed < 10000) { const left = Math.ceil((10000 - (Date.now() - lastPlayed)) / 1000); return await message.reply(`⏳ Подождите ${left} сек.`, replyParams()); }
            gameCooldowns.set(userId, Date.now());
        }

        if (cleanText.startsWith('краш')) {
            if (parts.length >= 3) {
                const autoStop = parseFloat(parts[1]); let betStr = parts[2]; let bet = parseAmount(betStr); if (bet === 'ALL') bet = balance;
                if (isNaN(autoStop) || autoStop < 1.01) return await message.reply("❌ Автостоп должен быть > 1.00", replyParams());
                if (isNaN(bet) || bet < 100) return await message.reply("❌ Мин. ставка 100$.", replyParams());
                if (bet > balance) return await message.reply(`❌ Недостаточно средств! Баланс: ${formatMoney(balance)}$.`, replyParams());
                await updateBalance(userId, -bet); const rand = Math.random(); let crashPoint = 1.00; if (rand > 0.03) crashPoint = Math.floor((1 / (1 - rand)) * 0.97 * 100) / 100;
                if (crashPoint >= autoStop) { const win = Math.floor(bet * autoStop); await updateBalance(userId, win); return await message.reply(`📈 Краш: x${crashPoint.toFixed(2)}\n\n✅ Выиграли ${formatMoney(win)}$!\n💰 Баланс: ${formatMoney(await getBalance(userId))}$`, replyParams()); }
                else { return await message.reply(`📈 Краш: x${crashPoint.toFixed(2)}\n\n❌ Проиграли ${formatMoney(bet)}$\n💰 Баланс: ${formatMoney(await getBalance(userId))}$`, replyParams()); }
            } return await message.reply("❌ краш [автостоп] [ставка]\nПример: краш 3 5кк", replyParams());
        }

        if (cleanText.startsWith('монетка')) {
            if (parts.length >= 3) {
                let side = ""; let betStr = "";
                if (['орел', 'решка'].includes(parts[1])) { side = parts[1]; betStr = parts[2]; } else if (['орел', 'решка'].includes(parts[2])) { side = parts[2]; betStr = parts[1]; } else return await message.reply("❌ Выберите 'орел' или 'решка'", replyParams());
                let bet = parseAmount(betStr); if (bet === 'ALL') bet = balance;
                if (isNaN(bet) || bet < 100) return await message.reply("❌ Мин. ставка 100$.", replyParams()); if (bet > balance) return await message.reply(`❌ Недостаточно средств! Баланс: ${formatMoney(balance)}$.`, replyParams());
                await updateBalance(userId, -bet); const res = Math.random() < 0.5 ? 'орел' : 'решка';
                if (res === side) { await updateBalance(userId, bet * 2); return await message.reply(`🪙 Выпал: ${res}\n\n✅ Выиграли ${formatMoney(bet * 2)}$!\n💰 Баланс: ${formatMoney(await getBalance(userId))}$`, replyParams()); }
                else { return await message.reply(`🪙 Выпал: ${res}\n\n❌ Проиграли ${formatMoney(bet)}$\n💰 Баланс: ${formatMoney(await getBalance(userId))}$`, replyParams()); }
            } return await message.reply("❌ монетка [орел/решка] [ставка]\nПример: монетка орел 100к", replyParams());
        }

        if (cleanText.startsWith('стакан')) {
            if (parts.length >= 3) {
                let cup = 0; let betStr = ""; const p1 = parseInt(parts[1]), p2 = parseInt(parts[2]);
                if (p1 >= 1 && p1 <= 3) { cup = p1; betStr = parts[2]; } else if (p2 >= 1 && p2 <= 3) { cup = p2; betStr = parts[1]; } else return await message.reply("❌ Выберите стакан (1-3)", replyParams());
                let bet = parseAmount(betStr); if (bet === 'ALL') bet = balance;
                if (isNaN(bet) || bet < 100) return await message.reply("❌ Мин. ставка 100$.", replyParams()); if (bet > balance) return await message.reply(`❌ Недостаточно средств! Баланс: ${formatMoney(balance)}$.`, replyParams());
                await updateBalance(userId, -bet); const res = Math.floor(Math.random() * 3) + 1;
                if (res === cup) { await updateBalance(userId, bet * 3); return await message.reply(`🥤 Шарик под стаканом ${res}\n\n✅ Выиграли ${formatMoney(bet * 3)}$!\n💰 Баланс: ${formatMoney(await getBalance(userId))}$`, replyParams()); }
                else { return await message.reply(`🥤 Шарик под стаканом ${res}\n\n❌ Проиграли ${formatMoney(bet)}$\n💰 Баланс: ${formatMoney(await getBalance(userId))}$`, replyParams()); }
            } return await message.reply("❌ стакан [1-3] [ставка]\nПример: стакан 2 100к", replyParams());
        }

        if (cleanText.startsWith('кубик')) {
            if (parts.length >= 3) {
                let guess = 0; let betStr = ""; const p1 = parseInt(parts[1]), p2 = parseInt(parts[2]);
                if (p1 >= 1 && p1 <= 6) { guess = p1; betStr = parts[2]; } else if (p2 >= 1 && p2 <= 6) { guess = p2; betStr = parts[1]; } else return await message.reply("❌ Выберите число (1-6)", replyParams());
                let bet = parseAmount(betStr); if (bet === 'ALL') bet = balance;
                if (isNaN(bet) || bet < 100) return await message.reply("❌ Мин. ставка 100$.", replyParams()); if (bet > balance) return await message.reply(`❌ Недостаточно средств! Баланс: ${formatMoney(balance)}$.`, replyParams());
                await updateBalance(userId, -bet); const res = Math.floor(Math.random() * 6) + 1;
                if (res === guess) { await updateBalance(userId, bet * 6); return await message.reply(`🎲 Выпало: ${res}\n\n✅ Выиграли ${formatMoney(bet * 6)}$!\n💰 Баланс: ${formatMoney(await getBalance(userId))}$`, replyParams()); }
                else { return await message.reply(`🎲 Выпало: ${res}\n\n❌ Проиграли ${formatMoney(bet)}$\n💰 Баланс: ${formatMoney(await getBalance(userId))}$`, replyParams()); }
            } return await message.reply("❌ кубик [1-6] [ставка]\nПример: кубик 4 100к", replyParams());
        }

        if (cleanText.startsWith('автомат')) {
            if (parts.length >= 2) {
                let bet = parseAmount(parts[1]); if (bet === 'ALL') bet = balance;
                if (isNaN(bet) || bet < 100) return await message.reply("❌ Мин. ставка 100$.", replyParams()); if (bet > balance) return await message.reply(`❌ Недостаточно средств! Баланс: ${formatMoney(balance)}$.`, replyParams());
                await updateBalance(userId, -bet); const emojis = ['🍒', '🍋', '🍇', '💎', '7️⃣']; const r1 = emojis[Math.floor(Math.random() * emojis.length)]; const r2 = emojis[Math.floor(Math.random() * emojis.length)]; const r3 = emojis[Math.floor(Math.random() * emojis.length)];
                let win = 0; if (r1 === r2 && r2 === r3) win = bet * 10; else if (r1 === r2 || r2 === r3 || r1 === r3) win = bet * 2;
                if (win > 0) { await updateBalance(userId, win); return await message.reply(`🎰 [ ${r1} | ${r2} | ${r3} ]\n\n✅ Выиграли ${formatMoney(win)}$!\n💰 Баланс: ${formatMoney(await getBalance(userId))}$`, replyParams()); }
                else { return await message.reply(`🎰 [ ${r1} | ${r2} | ${r3} ]\n\n❌ Проиграли ${formatMoney(bet)}$\n💰 Баланс: ${formatMoney(await getBalance(userId))}$`, replyParams()); }
            } return await message.reply("❌ автомат [ставка]\nПример: автомат 5кк", replyParams());
        }

        if (cleanText.startsWith('блэкджек')) {
            if (parts.length >= 2) {
                let bet = parseAmount(parts[1]); if (bet === 'ALL') bet = balance;
                if (isNaN(bet) || bet < 100) return await message.reply("❌ Мин. ставка 100$.", replyParams()); if (bet > balance) return await message.reply(`❌ Недостаточно средств! Баланс: ${formatMoney(balance)}$.`, replyParams());
                await updateBalance(userId, -bet); const playerScore = Math.floor(Math.random() * 10) + 12; const dealerScore = Math.floor(Math.random() * 10) + 12;
                let msgText = `🃏 Блэкджек\n\n👤 Твои очки: ${playerScore}\n🤵 Дилер: ${dealerScore}\n\n`;
                if (playerScore > 21) msgText += `❌ Перебор! Проиграли ${formatMoney(bet)}$`;
                else if (dealerScore > 21) { await updateBalance(userId, bet * 2); msgText += `✅ У дилера перебор! Выиграли ${formatMoney(bet * 2)}$`; }
                else if (playerScore > dealerScore) { await updateBalance(userId, bet * 2); msgText += `✅ Выиграли ${formatMoney(bet * 2)}$!`; }
                else if (playerScore === dealerScore) { await updateBalance(userId, bet); msgText += `🤝 Ничья! Ставка возвращена.`; }
                else msgText += `❌ Дилер выиграл! Проиграли ${formatMoney(bet)}$`;
                msgText += `\n💰 Баланс: ${formatMoney(await getBalance(userId))}$`; return await message.reply(msgText, replyParams());
            } return await message.reply("❌ блэкджек [ставка]\nПример: блэкджек 100к", replyParams());
        }

        if (cleanText.startsWith('дрим')) {
            if (parts.length >= 3) {
                let guess = 0; let betStr = ""; const validDream = [1, 2, 3, 4, 5]; const p1 = parseInt(parts[1]), p2 = parseInt(parts[2]);
                if (validDream.includes(p1)) { guess = p1; betStr = parts[2]; } else if (validDream.includes(p2)) { guess = p2; betStr = parts[1]; } else return await message.reply("❌ Числа: 1, 2, 3, 4, 5", replyParams());
                let bet = parseAmount(betStr); if (bet === 'ALL') bet = balance;
                if (isNaN(bet) || bet < 100) return await message.reply("❌ Мин. ставка 100$.", replyParams()); if (bet > balance) return await message.reply(`❌ Недостаточно средств! Баланс: ${formatMoney(balance)}$.`, replyParams());
                await updateBalance(userId, -bet); const res = Math.floor(Math.random() * 10) + 1; const validMultipliers = {1: 2, 2: 2, 3: 3, 4: 4, 5: 5};
                if (res === guess) { const win = bet * validMultipliers[guess]; await updateBalance(userId, win); return await message.reply(`💎 Выпало: ${res}\n\n✅ Выиграли ${formatMoney(win)}$ (x${validMultipliers[guess]})!\n💰 Баланс: ${formatMoney(await getBalance(userId))}$`, replyParams()); }
                else { return await message.reply(`💎 Выпало: ${res}\n\n❌ Проиграли ${formatMoney(bet)}$\n💰 Баланс: ${formatMoney(await getBalance(userId))}$`, replyParams()); }
            } return await message.reply("❌ дрим [1-5] [ставка]\nПример: дрим 5 100к", replyParams());
        }

        if (cleanText.includes('рулетка') || cleanText.startsWith('рул')) {
            if (parts.length >= 3) {
                let choice = ""; let betStr = "";
                if (parseAmount(parts[1]) > 0 || parseAmount(parts[1]) === 'ALL') { betStr = parts[1]; choice = parts[2]; } else { betStr = parts[parts.length - 1]; choice = parts[1]; }
                let bet = parseAmount(betStr); if (bet === 'ALL') bet = balance;
                if (isNaN(bet) || bet < 100) return await message.reply("❌ Мин. ставка 100$.", replyParams()); if (bet > balance) return await message.reply(`❌ Недостаточно средств! Баланс: ${formatMoney(balance)}$.`, replyParams());
                const res = Math.floor(Math.random() * 37); const redNumbers = [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36];
                let cName = redNumbers.includes(res) ? "Красное" : (res === 0 ? "Зеро" : "Черное"); let cEmoji = redNumbers.includes(res) ? "🔴" : (res === 0 ? "🟢" : "⚫"); let eName = res === 0 ? "Ноль" : (res % 2 === 0 ? "Четное" : "Нечетное");
                let win = (parseInt(choice) === res) || (["красное", "красный", "кр"].includes(choice) && redNumbers.includes(res)) || (["черное", "черный", "чр"].includes(choice) && !redNumbers.includes(res) && res !== 0) || (["чет", "четное"].includes(choice) && res % 2 === 0 && res !== 0) || (["нечет", "нечетное"].includes(choice) && res % 2 !== 0);
                if (win) { await updateBalance(userId, bet); return await message.reply(`🎰 Выпало: ${res} ${cEmoji} (${cName}, ${eName})\n\n✅ Выигрыш: +${bet}$\n💰 Баланс: ${formatMoney(await getBalance(userId))}$`, replyParams(isLs ? mainKb : undefined)); }
                else { await updateBalance(userId, -bet); return await message.reply(`🎰 Выпало: ${res} ${cEmoji} (${cName}, ${eName})\n\n😔 Проигрыш: -${bet}$\n💰 Баланс: ${formatMoney(await getBalance(userId))}$`, replyParams(isLs ? mainKb : undefined)); }
            } return await message.reply("❌ Формат: рулетка [красное/черное/чет/нечет] [ставка]", replyParams());
        }

        if (cleanText === 'фортуна') {
            const currentTime = Math.floor(Date.now() / 1000); const row = await dbGet("SELECT last_used FROM fortune_cd WHERE user_id = ?", [String(userId)]); const lastUse = row ? row.last_used : 0;
            if (currentTime - lastUse < FORTUNA_CD) { const remaining = FORTUNA_CD - (currentTime - lastUse); return await message.reply(`⏳ Фортуна через ${Math.floor(remaining / 60)} мин. ${remaining % 60} сек.`, replyParams()); }
            if (balance < 100) return await message.reply("❌ Фортуна стоит 100$.", replyParams());
            await updateBalance(userId, -100); await dbRun("REPLACE INTO fortune_cd (user_id, last_used) VALUES (?, ?)", [String(userId), currentTime]);
            const prize = [0, 50, 100, 200, 500, 1000, 5000][Math.floor(Math.random() * 7)]; await updateBalance(userId, prize);
            return await message.reply(`🎰 Выпало: ${formatMoney(prize)}$!\n💰 Баланс: ${formatMoney(await getBalance(userId))}$`, replyParams(isLs ? mainKb : undefined));
        }

        if (cleanText.startsWith('мины')) {
            let bet = 100; if (parts.length >= 2) { let parsed = parseAmount(parts[1]); if (parsed === 'ALL') bet = balance; else if (parsed > 0) bet = parsed; }
            if (isNaN(bet) || bet < 100) return await message.reply("❌ Мин. ставка 100$.", replyParams()); if (bet > balance) return await message.reply(`❌ Недостаточно средств! Баланс: ${formatMoney(balance)}$.`, replyParams());
            const gameId = String(Math.floor(Math.random() * 90000) + 10000); await dbRun("INSERT INTO games (game_id, user_id, bet, mines, opened, multiplier, msg_id, start_time) VALUES (?, ?, ?, '[]', '[]', 1.0, ?, 0)", [gameId, String(userId), bet, String(message.id)]);
            return await message.reply(`💣 Мины\nСтавка: ${bet}$\n\nВыберите количество мин (2-8):`, replyParams(getMinesCountKb(gameId)));
        }

        if (cleanText.startsWith('transfer') || cleanText.startsWith('перевод')) {
            if (parts.length >= 2 && message.hasReplyMessage) {
                const amount = parseAmount(parts[1]); const targetId = message.replyMessage.senderId;
                if (!amount || amount === 'ALL') return await message.reply("❌ Укажите сумму.", replyParams());
                if (targetId === userId) return await message.reply("❌ Нельзя перевести себе.", replyParams());
                if (targetId < 0) return await message.reply("❌ Нельзя переводить сообществам.", replyParams());
                if (amount < 50 || amount > 5000000000) return await message.reply("❌ Сумма от 50 до 5 000 000 000$", replyParams());
                if (balance < amount) return await message.reply("❌ Недостаточно средств.", replyParams());
                await updateBalance(userId, -amount); await updateBalance(targetId, amount);
                return await message.reply(`💸 Вы перевели ${formatMoney(amount)}$ игроку ${await getFullName(targetId)}.\n💰 Баланс: ${formatMoney(await getBalance(userId))}$`, replyParams());
            } else return await message.reply("❌ Формат: transfer [сумма] (ответом на сообщение)", replyParams());
        }

        if (cleanText.startsWith('duel')) {
            if (parts.length === 2) {
                const bet = parseAmount(parts[1]);
                if (!bet || bet === 'ALL') return await message.reply("❌ Укажите сумму.", replyParams());
                if (bet < 50 || bet > 2000) return await message.reply("❌ Ставка от 50 до 2000.", replyParams());
                if (balance < bet) return await message.reply("❌ Не хватает монет.", replyParams());
                const duelId = String(Math.floor(Math.random() * 90000) + 10000); await dbRun("REPLACE INTO active_duels (msg_id, challenger, bet, peer_id) VALUES (?, ?, ?, ?)", [duelId, String(userId), bet, String(peerId)]);
                return await message.reply(`⚔️ Дуэль!\n👤 Создатель: ${await getFullName(userId)}\n💰 Ставка: ${bet}$\n\n⚡ Нажми кнопку!`, replyParams(getDuelKb(duelId)));
            } else return await message.reply("❌ Формат: duel [сумма]", replyParams());
        }

        if (cleanText === 'бонус') {
            const currentTime = Math.floor(Date.now() / 1000); const row = await dbGet("SELECT last_used FROM bonus_cd WHERE user_id = ?", [String(userId)]); const lastUse = row ? row.last_used : 0;
            if (currentTime - lastUse < BONUS_CD) { const remaining = BONUS_CD - (currentTime - lastUse); return await message.reply(`⏳ Бонус через ${Math.floor(remaining / 60)} мин. ${remaining % 60} сек.`, replyParams()); }
            const bonusAmount = [100000, 200000, 500000][Math.floor(Math.random() * 3)]; await updateBalance(userId, bonusAmount); await dbRun("REPLACE INTO bonus_cd (user_id, last_used) VALUES (?, ?)", [String(userId), currentTime]); await dbRun("UPDATE users SET bonus_count = bonus_count + 1 WHERE user_id = ?", [String(userId)]);
            return await message.reply(`🎁 Бонус получен! ✨\n+${formatMoney(bonusAmount)}$\n💰 Баланс: ${formatMoney(await getBalance(userId))}$`, replyParams(isLs ? mainKb : undefined));
        }

        // ===== АДМИНСКИЕ КОМАНДЫ =====
        if (userId === ADMIN_ID) {
            if (cleanText === 'настройки') {
                const enabled = (await dbGet("SELECT value FROM settings WHERE key = 'antispam_enabled'")).value; const limit = (await dbGet("SELECT value FROM settings WHERE key = 'antispam_limit'")).value; const time = (await dbGet("SELECT value FROM settings WHERE key = 'antispam_time'")).value; const mute = (await dbGet("SELECT value FROM settings WHERE key = 'antispam_mute'")).value;
                return await message.reply(`⚙️ Настройки антиспама:\n\nСтатус: ${enabled === '1' ? "🟢 Включен" : "🔴 Выключен"}\n\nНажмите на кнопку, чтобы изменить.`, { keyboard: await getSettingsKb(enabled, limit, time, mute) });
            }

            if (cleanText.startsWith('unmute')) {
                const { targetId } = await getTargetAndReason(message, 'unmute');
                if (!targetId) return await message.reply("⚠️ Укажите пользователя (ответом или @упоминанием).", replyParams());
                try {
                    // Снимаем мут без параметра 'for'
                    await vk.api.messages.changeConversationMemberRestrictions({ group_id: GROUP_ID, peer_id: peerId, member_id: targetId, action: 'rw' });
                    const cacheKey = `${peerId}_${targetId}`; spamCache.delete(cacheKey);
                    return await message.reply(`✅ Вы успешно сняли мут с игрока ${await getFullName(targetId)}!`, replyParams());
                } catch (e) { return await message.reply(`⚠️ Не удалось снять мут. Ошибка: ${e.message}`, replyParams()); }
            }

            if (cleanText.startsWith('убрать')) {
                const targetQuery = cleanText.replace('убрать', '').trim().toLowerCase();
                if (targetQuery === 'all' || targetQuery === 'все' || targetQuery === 'всем') {
                    await dbRun("UPDATE users SET balance = 0, reputation = 0, xp = 0, level = 1, duel_wins = 0, bonus_count = 0");
                    return await message.reply(`💥 Все статы ВСЕХ игроков обнулены! (Машины и бизнесы остались)`, replyParams());
                } else {
                    const { targetId } = await getTargetAndReason(message, 'убрать');
                    if (!targetId) return await message.reply("⚠️ Ответьте на сообщение, укажите @ или 'all'.", replyParams());
                    await dbRun("UPDATE users SET balance = 0, reputation = 0, xp = 0, level = 1, duel_wins = 0, bonus_count = 0 WHERE user_id = ?", [String(targetId)]);
                    return await message.reply(`💥 Все статы игрока ${await getFullName(targetId)} обнулены! (Машины и бизнесы остались)`, replyParams());
                }
            }

            if (cleanText.startsWith('kick')) {
                if (parts.length === 1 && !message.hasReplyMessage) return await message.reply("🔔 /kick @VK Причина", replyParams());
                const { targetId, reason } = await getTargetAndReason(message, 'kick');
                if (!targetId) return await message.reply("⚠️ Пользователь не найден.", replyParams());
                if (targetId === ADMIN_ID) return await message.reply("❌ Нельзя исключить себя.", replyParams());
                if (!message.isChat) return await message.reply("❌ Только в беседе.", replyParams());
                const chatId = message.peerId - 2000000000; const targetName = await getFullName(targetId); const senderName = await getFullName(message.senderId);
                try { await vk.api.messages.removeChatUser({ chat_id: chatId, user_id: targetId, group_id: GROUP_ID }); return await message.reply(`${senderName} исключил(-а) ${targetName} по причине: "${reason}"`, replyParams()); }
                catch (e) { return await message.reply(`⚠️ Пользователь не в беседе или выше по статусу.`, replyParams()); }
            }

            if (cleanText.startsWith('чсб')) {
                if (parts.length === 1 && !message.hasReplyMessage) return await message.reply("🔔 /чсб @VK Причина", replyParams());
                const { targetId, reason } = await getTargetAndReason(message, 'чсб');
                if (!targetId) return await message.reply("⚠️ Пользователь не найден.", replyParams());
                if (targetId === ADMIN_ID) return await message.reply("❌ Нельзя занести себя в ЧС.", replyParams());
                await dbRun("REPLACE INTO blacklist (user_id, reason) VALUES (?, ?)", [String(targetId), reason]);
                return await message.reply(`🚫 ${await getFullName(message.senderId)} занес(-ла) в ЧС ${await getFullName(targetId)} по причине: "${reason}"`, replyParams());
            }

            if (cleanText.startsWith('разчсб')) {
                const { targetId } = await getTargetAndReason(message, 'разчсб');
                if (!targetId) return await message.reply("⚠️ Пользователь не найден.", replyParams());
                await dbRun("DELETE FROM blacklist WHERE user_id = ?", [String(targetId)]);
                return await message.reply(`✅ ${await getFullName(message.senderId)} разбанил(-а) ${await getFullName(targetId)} в ЧС бота.`, replyParams());
            }

            if (cleanText.startsWith('выдать')) {
                const args = message.text.split(' '); args.shift(); let amount = 0; let remainingArgs = [];
                for (const arg of args) { const parsed = parseAmount(arg); if (parsed > 0 && parsed !== 'ALL') amount = parsed; else remainingArgs.push(arg); }
                if (amount <= 0) return await message.reply("❌ Укажите сумму.", replyParams());
                const targetQuery = remainingArgs.join(' ').trim().toLowerCase();
                if (targetQuery === 'all' || targetQuery === 'все' || targetQuery === 'всем') { await dbRun("UPDATE users SET balance = balance + ?", [amount]); return await message.reply(`💰 Владелец выдал всем по ${formatMoney(amount)}$!`, replyParams()); }
                else {
                    let targetId = null; if (message.hasReplyMessage) targetId = message.replyMessage.senderId;
                    else if (targetQuery) { const mentionMatch = targetQuery.match(/@([a-zA-Z0-9._]+)/i) || targetQuery.match(/\[id(\d+)\|/); const urlMatch = targetQuery.match(/(?:https?:\/\/)?(?:vk\.com|vk\.ru)\/([a-zA-Z0-9._]+)/i);
                        if (mentionMatch) { if (mentionMatch[1].match(/^\d+$/)) targetId = parseInt(mentionMatch[1]); else { try { const res = await vk.api.utils.resolveScreenName({ screen_name: mentionMatch[1] }); if (res.type === 'user') targetId = res.object_id; } catch (e) {} } }
                        else if (urlMatch) { try { const res = await vk.api.utils.resolveScreenName({ screen_name: urlMatch[1] }); if (res.type === 'user') targetId = res.object_id; } catch (e) {} }
                    }
                    if (!targetId) return await message.reply("⚠️ Укажите пользователя или 'all'.", replyParams());
                    await updateBalance(targetId, amount); return await message.reply(`💰 Владелец выдал ${formatMoney(amount)}$ игроку ${await getFullName(targetId)}!`, replyParams());
                }
            }

            if (cleanText.startsWith('обнулить')) {
                const args = message.text.split(' '); args.shift(); const targetQuery = args.join(' ').trim().toLowerCase();
                if (targetQuery === 'all') { await dbRun("UPDATE users SET balance = 0"); await dbRun("UPDATE businesses SET balance = 0"); return await message.reply("💥 Балансы ВСЕХ игроков и их бизнесов обнулены!", replyParams()); }
                else {
                    const { targetId } = await getTargetAndReason(message, 'обнулить');
                    if (!targetId) return await message.reply("⚠️ Укажите 'all', @ или ответом.", replyParams());
                    await dbRun("UPDATE users SET balance = 0 WHERE user_id = ?", [String(targetId)]); await dbRun("UPDATE businesses SET balance = 0 WHERE user_id = ?", [String(targetId)]);
                    return await message.reply(`💥 Баланс игрока ${await getFullName(targetId)} и его бизнеса обнулен!`, replyParams());
                }
            }

            if (cleanText === 'cp') { await dbRun("DELETE FROM promos"); return await message.reply("✅ Все промокоды удалены.", replyParams()); }
            if (cleanText.startsWith('создать')) {
                if (parts.length === 4) {
                    const amt = parseAmount(parts[2]); const lim = parseAmount(parts[3]);
                    if (amt > 0 && lim > 0) { await dbRun("REPLACE INTO promos (code, amount, limit_count, used_by) VALUES (?, ?, ?, '')", [parts[1], amt, lim]); return await message.reply(`✅ Промокод \`${parts[1]}\` создан!`, replyParams()); }
                } return await message.reply("❌ Формат: /создать [код] [сумма] [лимит]", replyParams());
            }
        }

        if (cleanText === 'промолист') {
            const rows = await dbAll("SELECT code, amount, limit_count, used_by FROM promos"); if (rows.length === 0) return await message.reply("❌ Активных промокодов нет.", replyParams());
            let promoList = "🎁 Активные промокоды:\n\n"; for (const r of rows) { const usedCount = r.used_by ? r.used_by.split(",").length : 0; promoList += `▪️ \`${r.code}\` — ${formatMoney(r.amount)}$ (${usedCount}/${r.limit_count})\n`; }
            return await message.reply(promoList, replyParams());
        }

        if (cleanText.startsWith('promo')) {
            if (parts.length === 2) {
                try { const isMember = await vk.api.groups.isMember({ group_id: GROUP_ID, user_id: userId }); if (isMember !== 1) { const subKb = Keyboard.builder().inline().urlButton({ label: '📢 Подписаться', url: `https://vk.com/public${GROUP_ID}` }); return await message.reply("⚠️ Промокоды только для подписчиков!", replyParams(subKb.toString())); } } catch (e) {}
                const row = await dbGet("SELECT amount, limit_count, used_by FROM promos WHERE code = ?", [parts[1]]); if (!row) return await message.reply("❌ Промокод не существует или исчерпан.", replyParams());
                const usedBy = row.used_by ? row.used_by.split(",") : []; if (usedBy.length >= row.limit_count) { await dbRun("DELETE FROM promos WHERE code = ?", [parts[1]]); return await message.reply("❌ Промокод больше не действителен.", replyParams()); }
                if (usedBy.includes(String(userId))) return await message.reply("❌ Вы уже активировали этот промокод!", replyParams());
                usedBy.push(String(userId)); await updateBalance(userId, row.amount);
                if (usedBy.length >= row.limit_count) { await dbRun("DELETE FROM promos WHERE code = ?", [parts[1]]); return await message.reply(`✅ Активирован! +${row.amount}$\n⚠️ Промокод удален (лимит исчерпан).`, replyParams()); }
                else { await dbRun("UPDATE promos SET used_by = ? WHERE code = ?", [usedBy.join(","), parts[1]]); return await message.reply(`✅ Активирован! +${row.amount}$\nОсталось: ${row.limit_count - usedBy.length}`, replyParams()); }
            } else return await message.reply("❌ Формат: /promo [код]", replyParams());
        }
    } catch (error) { console.error("ОШИБКА ПРИ ОБРАБОТКЕ:", error); try { await message.reply(`⚠️ Ошибка: ${error.message}`, { disable_mentions: 1 }); } catch (e) {} }
});

vk.updates.on('message_event', async (context) => {
    let answered = false; const safeAnswer = async (params) => { if (!answered) { answered = true; await context.answer(params).catch(() => {}); } };
    try {
        const payload = context.eventPayload; const userId = context.userId;
        if ((payload.cmd === 'top_menu' || payload.cmd === 'top_back' || payload.cmd === 'biz_upgrade') && payload.author) { if (String(userId) !== String(payload.author)) return await safeAnswer({ type: 'show_snackbar', text: '❌ Это меню вызвано другим пользователем.' }); }

        if (payload.cmd === 'settings_toggle') {
            if (userId !== ADMIN_ID) return await safeAnswer({ type: 'show_snackbar', text: '❌ Только владелец.' });
            await dbRun("UPDATE settings SET value = ? WHERE key = 'antispam_enabled'", [payload.state]);
            await safeAnswer();
            const limit = (await dbGet("SELECT value FROM settings WHERE key = 'antispam_limit'")).value; const time = (await dbGet("SELECT value FROM settings WHERE key = 'antispam_time'")).value; const mute = (await dbGet("SELECT value FROM settings WHERE key = 'antispam_mute'")).value;
            await vk.api.messages.edit({ peer_id: context.peerId, message: `⚙️ Настройки антиспама:\n\nСтатус: ${payload.state === '1' ? "🟢 Включен" : "🔴 Выключен"}\n\nНажмите на кнопку, чтобы изменить.`, keyboard: await getSettingsKb(payload.state, limit, time, mute), conversation_message_id: context.conversationMessageId });
            return;
        }

        if (payload.cmd === 'settings_edit') {
            if (userId !== ADMIN_ID) return await safeAnswer({ type: 'show_snackbar', text: '❌ Только владелец.' });
            await safeAnswer(); adminStates.set(userId, payload.field);
            let fieldName = ""; if (payload.field === 'limit') fieldName = "лимит сообщений (например, 5)"; if (payload.field === 'time') fieldName = "время (сек) (например, 60)"; if (payload.field === 'mute') fieldName = "мут (мин) (например, 10)";
            await vk.api.messages.send({ peer_id: context.peerId, message: `✏️ Введите новое значение: ${fieldName}`, random_id: Math.floor(Math.random() * 1000000000) });
            return;
        }

        if (payload.cmd === 'help_start') { await safeAnswer(); await vk.api.messages.edit({ peer_id: context.peerId, message: "📖 Выберите раздел:", keyboard: getHelpKb(), conversation_message_id: context.conversationMessageId }); return; }
        if (payload.cmd === 'help_menu') {
            await safeAnswer(); let msg = "";
            if (payload.section === 'games') msg = "🎰 Игры:\n/рулетка [цвет/чет] [ставка]\n/краш [автостоп] [ставка]\n/монетка [орел/решка] [ставка]\n/стакан [1-3] [ставка]\n/кубик [1-6] [ставка]\n/автомат [ставка]\n/блэкджек [ставка]\n/дрим [1-5] [ставка]\n/мины [ставка]\n/фортуна\n\n⚠️ Мин. ставка: 100$. Ставка 'вб' разрешена.";
            if (payload.section === 'eco') msg = "💼 Экономика:\n/бизнес\n/купитьбиз [название]\n/мойбизнес\n/вывести\n/закрыть бизнес\n/бонус\n/transfer [сумма] (ответом)\n/duel [сумма]\n/promo [код]\n/промолист\n/машины\n/купить машина [название]";
            if (payload.section === 'profile') msg = "👤 Профиль и прочее:\n/профиль\n/топ\n/rep +/- (ответом)\n/пинг\n\n💡 Слэш (/) в начале писать необязательно!";
            await vk.api.messages.edit({ peer_id: context.peerId, message: msg, keyboard: getHelpBackKb(), conversation_message_id: context.conversationMessageId }); return;
        }

        if (payload.cmd === 'casino_info') {
            let msg = "";
            if (payload.game === 'roulette') msg = "Как играть в рулетку ❓\n\"Рулетка [ставка] [цвет/чет]\"\n▪ Число от 0 до 36 (x36)\n▪ Чет (x2)\n▪ Нечет (x2)\n▪ Красное (x2)\n▪ Черное (x2)\n▪ 1-12 (x3)\n▪ 13-24 (x3)\n▪ 25-36 (x3)\n▪ 1-18 (x2)\n▪ 19-36 (x2)\n▪ Ряд1\n▪ Ряд2\n▪ Ряд3\n\n⚠️ Мин. ставка: 100$. Ставка 'вб' разрешена.\n\nПример — \"Рулетка чет 5кк\"";
            if (payload.game === 'crash') msg = "❌ краш (автостоп) (ставка)\n\nПример: краш 3 5кк";
            if (payload.game === 'coin') msg = "❌ монетка [орел/решка] [ставка]\n\nПример: монетка орел 100к";
            if (payload.game === 'glass') msg = "❌ стакан [1-3] [ставка]\n\nПример: стакан 2 100к";
            if (payload.game === 'dice') msg = "❌ кубик [1-6] [ставка]\n\nПример: кубик 4 100к";
            if (payload.game === 'slot') msg = "автомат (сумма)\n\nПример: автомат 5кк";
            if (payload.game === 'blackjack') msg = "❌ Блэкджек (ставка)\n\nПример: блэкджек 100к";
            if (payload.game === 'dream') msg = "Дрим [число] [ставка]\n-Доступны числа:\n🔹 1 (x2)\n🔹 2 (x2)\n🔹 3 (x3)\n🔹 4 (x4)\n🔹 5 (x5)\n\n🤔 Пример: дрим 5 100к";
            await safeAnswer(); await vk.api.messages.send({ peer_id: context.peerId, message: msg, random_id: Math.floor(Math.random() * 1000000000), disable_mentions: 1 }); return;
        }

        if (payload.cmd === 'biz_upgrade') {
            const biz = await dbGet("SELECT * FROM businesses WHERE user_id = ?", [String(userId)]);
            if (!biz) return await safeAnswer({ type: 'show_snackbar', text: '❌ У вас нет бизнеса.' });
            if (biz.level >= 5) return await safeAnswer({ type: 'show_snackbar', text: '❌ Максимальный уровень!' });
            const bizData = Object.values(BIZ_DATA).find(b => b.name === biz.biz_name) || { name: biz.biz_name, baseIncome: 1000 }; const timePassed = Date.now() - biz.last_income; const earned = Math.floor(timePassed * ((bizData.baseIncome * biz.level) / 180000)); const totalBalance = Number(biz.balance) + earned; const nextLevelCost = (Number(biz.level) === 1 ? 2000000 : Number(biz.level) === 2 ? 5000000 : Number(biz.level) * 5000000);
            const userBal = await getBalance(userId); if (userBal < nextLevelCost) return await safeAnswer({ type: 'show_snackbar', text: '❌ Не хватает денег на балансе!' });
            await safeAnswer(); await updateBalance(userId, -nextLevelCost); await dbRun("UPDATE businesses SET level = level + 1, balance = ?, last_income = ? WHERE user_id = ?", [totalBalance, Date.now(), String(userId)]);
            const newMsgText = `🏢 Бизнес ${await getFullName(userId)}\n${biz.biz_name}\n\n💪 Уровень: ${biz.level + 1}/5\n🐱 ${formatMoney(bizData.baseIncome * (biz.level + 1) * 20)}$/час\n💸 На балансе бизнеса: ${formatMoney(totalBalance)}$\n\nПовышение уровня стоит: ${formatMoney((biz.level + 1) * 5000000)}$\n\n👉 Чтобы вывести деньги, напишите /вывести`;
            await vk.api.messages.edit({ peer_id: context.peerId, message: newMsgText, keyboard: getBizKb(userId), disable_mentions: 1, conversation_message_id: context.conversationMessageId }); return;
        }

        if (payload.cmd === 'work_do') {
            const now = Date.now(); const workRow = await dbGet("SELECT count, last_reset FROM work_cd WHERE user_id = ?", [String(userId)]); let count = workRow ? Number(workRow.count) : 0; let lastReset = workRow ? Number(workRow.last_reset) : 0;
            if (now - lastReset >= 3600000) { count = 0; lastReset = now; }
            if (count >= 3) { const remaining = 3600000 - (now - lastReset); const m = Math.floor(remaining / 60000); const s = Math.floor((remaining % 60000) / 1000); return await safeAnswer({ type: 'show_snackbar', text: `⏳ Ждите ${m} мин. ${s} сек.` }); }
            if (payload.type === 'Такси') { const userRow = await dbGet("SELECT car FROM users WHERE user_id = ?", [String(userId)]); if (!userRow || !userRow.car) return await safeAnswer({ type: 'show_snackbar', text: '❌ Для такси нужна машина! Купите в /машины' }); }
            await safeAnswer(); count++; await dbRun("REPLACE INTO work_cd (user_id, count, last_reset) VALUES (?, ?, ?)", [String(userId), count, lastReset]);
            const isLucky = Math.random() > 0.3; let earned = 0; let msgText = "";
            if (isLucky) { earned = 2000000; await updateBalance(userId, earned); msgText = `✅ Вы успешно поработали (${payload.type}) и заработали ${formatMoney(earned)}$!`; }
            else msgText = `😢 Не повезло! Вы работали (${payload.type}), но заработали 0$.`;
            const newBal = await getBalance(userId); await vk.api.messages.edit({ peer_id: context.peerId, message: `${msgText}\n\n💰 Ваш баланс: ${formatMoney(newBal)}$\n📊 Осталось попыток: ${3 - count}/3`, keyboard: getWorkKb(), conversation_message_id: context.conversationMessageId }); return;
        }

        await safeAnswer();
        if (payload.cmd === 'work_menu') { await vk.api.messages.edit({ peer_id: context.peerId, message: "💼 Выберите работу:", keyboard: getWorkKb(), conversation_message_id: context.conversationMessageId }); return; }

        if (payload.cmd === 'activate_bot' || payload.cmd === 'decline_bot') {
            try {
                const members = await vk.api.messages.getConversationMembers({ peer_id: context.peerId }); const clicker = members.items.find(m => m.member_id === userId); const isClickerAdmin = clicker && (clicker.is_admin || clicker.is_owner);
                if (!isClickerAdmin && userId !== ADMIN_ID) return await vk.api.messages.edit({ peer_id: context.peerId, message: "❌ Только администраторы беседы могут это сделать!", keyboard: "", conversation_message_id: context.conversationMessageId });
                const bot = members.items.find(m => m.member_id == -GROUP_ID || m.member_id == GROUP_ID); const isBotAdmin = bot && bot.is_admin;
                if (payload.cmd === 'activate_bot') {
                    if (!isBotAdmin) return await vk.api.messages.edit({ peer_id: context.peerId, message: "❌ Ошибка. Убедитесь, что бот администратор.", keyboard: "", conversation_message_id: context.conversationMessageId });
                    await vk.api.messages.edit({ peer_id: context.peerId, message: "🎉 Вы подключили бота!\nПодробности /help", disable_mentions: 1, keyboard: "", conversation_message_id: context.conversationMessageId });
                } else await vk.api.messages.edit({ peer_id: context.peerId, message: "❌ Активация отменена. Добавьте бота заново.", disable_mentions: 1, keyboard: "", conversation_message_id: context.conversationMessageId });
                return;
            } catch (e) { return await vk.api.messages.edit({ peer_id: context.peerId, message: "❌ Ошибка при проверке прав.", keyboard: "", conversation_message_id: context.conversationMessageId }); }
        }

        if (payload.cmd === 'top_menu') {
            const type = payload.type; const scope = payload.scope; const repType = payload.repType || 'pos'; let orderBy = "balance DESC"; let filter = "balance > 2";
            if (type === 'rep') { if (repType === 'pos') { orderBy = "reputation DESC"; filter = "reputation > 0"; } else { orderBy = "reputation ASC"; filter = "reputation < 0"; } }
            else if (type === 'level') { orderBy = "level DESC, xp DESC"; filter = "level > 1"; } else if (type === 'duels') { orderBy = "duel_wins DESC"; filter = "duel_wins > 0"; } else if (type === 'bonus') { orderBy = "bonus_count DESC"; filter = "bonus_count > 0"; }
            let rows = []; if (scope === 'global') rows = await dbAll(`SELECT user_id, balance, reputation, level, xp, duel_wins, bonus_count FROM users WHERE ${filter} ORDER BY ${orderBy} LIMIT 10`);
            else { const chatUsers = await dbAll("SELECT user_id FROM chat_messages WHERE peer_id = ?", [String(context.peerId)]); if (chatUsers.length > 0) { const ids = chatUsers.map(u => `'${u.user_id}'`).join(','); rows = await dbAll(`SELECT user_id, balance, reputation, level, xp, duel_wins, bonus_count FROM users WHERE user_id IN (${ids}) AND ${filter} ORDER BY ${orderBy} LIMIT 10`); } }
            if (rows.length === 0) { await vk.api.messages.edit({ peer_id: context.peerId, message: "❌ Топ пуст.", keyboard: getTopKb(payload.author, type, scope, repType), conversation_message_id: context.conversationMessageId }); return; }
            const userIds = rows.map(r => r.user_id); let usersInfo = []; try { usersInfo = await vk.api.users.get({ user_ids: userIds.join(','), fields: 'deactivated' }); } catch (e) {}
            let title = `🏆 ТОП 10 (${scope === 'global' ? 'Общий' : 'В беседе'})\n`; if (type === 'coins') title += "💰 По монетам\n\n"; if (type === 'level') title += "📊 По уровню\n\n"; if (type === 'duels') title += "⚔️ По победам в дуэлях\n\n"; if (type === 'bonus') title += "🎁 По бонусам\n\n"; if (type === 'rep') title += `⭐ По репутации (${repType === 'pos' ? 'Положительная' : 'Отрицательная'})\n\n`;
            let topText = title; let count = 0; const emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"];
            for (const r of rows) { const uInfo = usersInfo.find(u => u.id == r.user_id); if (uInfo && !uInfo.deactivated) { let value = ""; if (type === 'coins') value = `${formatMoney(r.balance)}$`; if (type === 'level') value = `Ур. ${r.level} (${r.xp} XP)`; if (type === 'rep') value = `${r.reputation > 0 ? '+' : ''}${r.reputation}`; if (type === 'duels') value = `${r.duel_wins} побед`; if (type === 'bonus') value = `${r.bonus_count} бонусов`; topText += `${emojis[count]} [id${uInfo.id}|${uInfo.first_name} ${uInfo.last_name || ''}] — ${value}\n`; count++; } }
            await vk.api.messages.edit({ peer_id: context.peerId, message: topText, keyboard: getTopKb(payload.author, type, scope, repType), disable_mentions: 1, conversation_message_id: context.conversationMessageId }); return;
        }

        if (payload.cmd === 'top_back') {
            const rows = await dbAll("SELECT user_id, count FROM chat_messages WHERE peer_id = ? ORDER BY count DESC LIMIT 10", [String(context.peerId)]); let topText = "⭐ ТОП 10 ПО СООБЩЕНИЯМ\n\n";
            if (rows.length > 0) { const userIds = rows.map(r => r.user_id); let usersInfo = []; try { usersInfo = await vk.api.users.get({ user_ids: userIds.join(','), fields: 'deactivated' }); } catch (e) {} let count = 0; const emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]; for (const r of rows) { const uInfo = usersInfo.find(u => u.id == r.user_id); if (uInfo && !uInfo.deactivated) { topText += `${emojis[count]} [id${uInfo.id}|${uInfo.first_name} ${uInfo.last_name || ''}] - ${r.count} сообщений\n`; count++; } } }
            else topText += "В этой беседе еще никто не писал.";
            await vk.api.messages.edit({ peer_id: context.peerId, message: topText, keyboard: getTopKb(payload.author, 'coins', 'chat'), disable_mentions: 1, conversation_message_id: context.conversationMessageId }); return;
        }

        if (payload.cmd === 'duel_accept') {
            const row = await dbGet("SELECT challenger, bet FROM active_duels WHERE msg_id = ?", [payload.duel_id]);
            if (row) {
                if (String(userId) === row.challenger) return await vk.api.messages.edit({ peer_id: context.peerId, message: "❌ Нельзя драться с собой!", keyboard: "", conversation_message_id: context.conversationMessageId });
                if (await getBalance(userId) < row.bet) return await vk.api.messages.edit({ peer_id: context.peerId, message: "❌ Не хватает денег!", keyboard: "", conversation_message_id: context.conversationMessageId });
                const winnerId = Math.random() < 0.5 ? parseInt(row.challenger) : userId; const loserId = winnerId === userId ? parseInt(row.challenger) : userId; const prize = Math.floor(row.bet * 1.8);
                await updateBalance(winnerId, prize); await updateBalance(loserId, -row.bet); await dbRun("UPDATE users SET duel_wins = duel_wins + 1 WHERE user_id = ?", [String(winnerId)]); await dbRun("DELETE FROM active_duels WHERE msg_id = ?", [payload.duel_id]);
                await vk.api.messages.edit({ peer_id: context.peerId, message: `⚔️ Дуэль завершена!\n\n🏆 Победитель: ${await getFullName(winnerId)}\n❌ Проигравший: ${await getFullName(loserId)}\n\n💰 Выигрыш: ${prize}$`, keyboard: "", disable_mentions: 1, conversation_message_id: context.conversationMessageId }); return;
            }
        }

        if (payload.cmd === 'mines_set') {
            const gameId = String(payload.gameId); const count = Number(payload.count);
            try {
                const row = await dbGet("SELECT bet FROM games WHERE game_id = ? AND user_id = ?", [gameId, String(userId)]); if (!row) return;
                const minesArr = []; while(minesArr.length < count) { const r = Math.floor(Math.random() * 9) + 1; if (!minesArr.includes(r)) minesArr.push(r); }
                await dbRun("UPDATE games SET mines = ?, opened = '[]', multiplier = 1.0, start_time = ? WHERE game_id = ?", [JSON.stringify(minesArr), Date.now(), gameId]);
                const ui = getMinesGameUI(gameId, row.bet, count, minesArr, [], false, null, await getFullName(userId), await getBalance(userId), 60);
                await vk.api.messages.edit({ peer_id: context.peerId, message: ui.text, keyboard: ui.kb, conversation_message_id: context.conversationMessageId }); return;
            } catch(e) { return; }
        }

        if (payload.cmd === 'mines_click') {
            const gameId = String(payload.gameId); const cell = Number(payload.cell);
            try {
                const row = await dbGet("SELECT bet, mines, opened, multiplier, start_time FROM games WHERE game_id = ? AND user_id = ?", [gameId, String(userId)]); if (!row) return;
                const bet = row.bet; const mines = JSON.parse(row.mines); const opened = JSON.parse(row.opened); const startTime = row.start_time;
                if (Date.now() - startTime > 60000) { await updateBalance(userId, -bet); await dbRun("DELETE FROM games WHERE game_id = ?", [gameId]); const balance = await getBalance(userId); const ui = getMinesGameUI(gameId, bet, mines.length, mines, opened, true, null, await getFullName(userId), balance); await vk.api.messages.edit({ peer_id: context.peerId, message: ui.text.replace('наступил(а) на мину!', 'не успел(а) открыть клетку!'), keyboard: ui.kb, conversation_message_id: context.conversationMessageId }); return; }
                if (opened.includes(cell)) return; opened.push(cell); let isLoss = false; let hitCell = null; let currentMoney = 0;
                if (mines.includes(cell)) { isLoss = true; hitCell = cell; await updateBalance(userId, -bet); await dbRun("DELETE FROM games WHERE game_id = ?", [gameId]); }
                else {
                    let currentMult = 1.0; for (let i = 0; i < opened.length; i++) currentMult *= (9 - i) / (9 - mines.length - i); currentMult = Math.round(currentMult * 0.95 * 100) / 100; currentMoney = Math.floor(bet * currentMult);
                    if (opened.length === (9 - mines.length)) { await updateBalance(userId, currentMoney); await dbRun("DELETE FROM games WHERE game_id = ?", [gameId]); isLoss = true; hitCell = -1; }
                    else await dbRun("UPDATE games SET opened = ?, multiplier = ? WHERE game_id = ?", [JSON.stringify(opened), currentMult, gameId]);
                }
                const balance = await getBalance(userId); const name = await getFullName(userId);
                if (isLoss) { const ui = getMinesGameUI(gameId, bet, mines.length, mines, opened, true, hitCell, name, balance); let text = ui.text; if (hitCell === -1) text = `🏆 ПОБЕДА!\n────────────────────\n👤 ${name}\n💣 Мин на поле: ${mines.length}\n✅ Успел(а) открыть: ${opened.length}\n\n📈 Выигрыш: +${currentMoney} 💰 (x${(currentMoney/bet).toFixed(2)})\n💳 Баланс: ${formatMoney(balance)} 💰\n\n💬 Поздравляем! Ты забрал всё! 🎉`; await vk.api.messages.edit({ peer_id: context.peerId, message: text, keyboard: ui.kb, conversation_message_id: context.conversationMessageId }); }
                else { const ui = getMinesGameUI(gameId, bet, mines.length, mines, opened, false, null, name, balance); const timeLeft = Math.max(0, Math.floor((60000 - (Date.now() - startTime)) / 1000)); await vk.api.messages.edit({ peer_id: context.peerId, message: ui.text.replace('{TIME}', timeLeft.toString()), keyboard: ui.kb, conversation_message_id: context.conversationMessageId }); }
                return;
            } catch (e) { return; }
        }

        if (payload.cmd === 'mines_cashout') {
            const gameId = String(payload.gameId);
            try {
                const row = await dbGet("SELECT bet, multiplier, mines, opened FROM games WHERE game_id = ? AND user_id = ?", [gameId, String(userId)]); if (!row) return;
                const opened = JSON.parse(row.opened); if (opened.length === 0) return;
                const winAmount = Math.floor(row.bet * row.multiplier); await updateBalance(userId, winAmount); await dbRun("DELETE FROM games WHERE game_id = ?", [gameId]);
                const balance = await getBalance(userId); const mines = JSON.parse(row.mines);
                await vk.api.messages.edit({ peer_id: context.peerId, message: `💰 ВЫВОД\n────────────────────\n👤 ${await getFullName(userId)}\n💵 Забрал: ${winAmount} 💰 (x${row.multiplier})\n💳 Баланс: ${formatMoney(balance)} 💰\n\n💬 Отличная игра! Заходи ещё 🍀`, keyboard: buildMinesKb(gameId, opened, mines, true, null), conversation_message_id: context.conversationMessageId }); return;
            } catch(e) { return; }
        }
    } catch (e) { console.error("КРИТИЧЕСКАЯ Ошибка в кнопках:", e); await safeAnswer({ type: 'show_snackbar', text: '⚠️ Ошибка. Попробуйте позже.' }); }
});

console.log("ПОПЫТКА ЗАПУСКА БОТА...");
vk.updates.startPolling().then(() => { console.log("--- БОТ УСПЕШНО ЗАПУЩЕН (LONGPOLL) ---"); }).catch(err => { console.error("ОШИБКА ПРИ СТАРТЕ:", err); });
