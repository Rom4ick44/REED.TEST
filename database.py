# database.py
import asyncpg
import json
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from config import PG_HOST, PG_PORT, PG_DATABASE, PG_USER, PG_PASSWORD

# Формируем DSN
DB_DSN = f"postgresql://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DATABASE}"

_pool: Optional[asyncpg.Pool] = None

async def init_db():
    """Инициализация пула соединений и создание таблиц."""
    global _pool
    _pool = await asyncpg.create_pool(DB_DSN, min_size=2, max_size=10)
    
    async with _pool.acquire() as conn:
        # Таблица чёрного списка
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS blacklist (
                user_id BIGINT PRIMARY KEY,
                reason TEXT,
                date TIMESTAMP,
                moderator_id BIGINT
            )
        ''')
        
        # Таблица заявок
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS applications (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                answers JSONB,
                status TEXT DEFAULT 'pending',
                reviewer_id BIGINT,
                message_id BIGINT,
                ping_message_id BIGINT,
                claimed_by BIGINT,
                date TIMESTAMP DEFAULT NOW()
            )
        ''')
        
        # Таблица настроек
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        await conn.execute("INSERT INTO settings (key, value) VALUES ('applications_open', 'true') ON CONFLICT (key) DO NOTHING")
        
        # Портфели
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS portfolios (
                channel_id BIGINT PRIMARY KEY,
                owner_id BIGINT NOT NULL,
                rank TEXT NOT NULL,
                tier INTEGER DEFAULT 0,
                pinned_by BIGINT,
                thread_rp_id BIGINT,
                thread_gang_id BIGINT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        ''')
        
        # AFK
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS afk (
                user_id BIGINT PRIMARY KEY,
                start_time DOUBLE PRECISION NOT NULL,
                duration_seconds INTEGER NOT NULL,
                reason TEXT NOT NULL,
                channel_id BIGINT,
                notified_expired INTEGER DEFAULT 0
            )
        ''')
        
        # Отпуска
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS vacations (
                user_id BIGINT PRIMARY KEY,
                start_time DOUBLE PRECISION NOT NULL,
                duration_text TEXT NOT NULL,
                reason TEXT NOT NULL,
                channel_id BIGINT
            )
        ''')
        
        # Статистика игроков
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS player_stats (
                user_id BIGINT PRIMARY KEY,
                accepted_by BIGINT,
                accepted_date TIMESTAMP,
                warns INTEGER DEFAULT 0,
                points INTEGER DEFAULT 0,
                voice_time INTEGER DEFAULT 0,
                last_updated TIMESTAMP
            )
        ''')
        
        # Запросы повышения
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS promotion_requests (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                reason TEXT,
                status TEXT DEFAULT 'pending',
                requested_at TIMESTAMP DEFAULT NOW(),
                reviewed_by BIGINT,
                reviewed_at TIMESTAMP
            )
        ''')
        
        # Запросы разбора отката
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS vod_requests (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                vod_link TEXT,
                description TEXT,
                status TEXT DEFAULT 'pending',
                requested_at TIMESTAMP DEFAULT NOW(),
                reviewed_by BIGINT,
                reviewed_at TIMESTAMP
            )
        ''')
        
        # Запросы грина
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS green_requests (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                amount INTEGER,
                level INTEGER,
                status TEXT DEFAULT 'pending',
                requested_at TIMESTAMP DEFAULT NOW(),
                granted_by BIGINT,
                granted_at TIMESTAMP,
                channel_id BIGINT,
                message_id BIGINT,
                thread_id BIGINT
            )
        ''')
        
        # Мероприятия
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id SERIAL PRIMARY KEY,
                message_id_info BIGINT NOT NULL,
                message_id_main BIGINT NOT NULL,
                message_id_sub BIGINT NOT NULL,
                channel_id BIGINT NOT NULL,
                creator_id BIGINT NOT NULL,
                type TEXT NOT NULL,
                title TEXT NOT NULL,
                server TEXT,
                time TEXT NOT NULL,
                map TEXT,
                "limit" INTEGER NOT NULL,
                group_name TEXT,
                is_open INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT NOW()
            )
        ''')
        
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS event_participants (
                id SERIAL PRIMARY KEY,
                event_id INTEGER REFERENCES events(id) ON DELETE CASCADE,
                user_id BIGINT NOT NULL,
                role TEXT NOT NULL
            )
        ''')
        
        # Логи
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                id SERIAL PRIMARY KEY,
                guild_id BIGINT NOT NULL,
                user_id BIGINT,
                action_type TEXT NOT NULL,
                details TEXT,
                timestamp TIMESTAMP DEFAULT NOW()
            )
        ''')
        
        # Кики
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS kicks (
                id SERIAL PRIMARY KEY,
                guild_id BIGINT NOT NULL,
                moderator_id BIGINT,
                user_id BIGINT,
                reason TEXT,
                kick_type TEXT,
                static TEXT,
                timestamp TIMESTAMP DEFAULT NOW(),
                status TEXT DEFAULT 'active'
            )
        ''')
        
        # Оружие
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS weapons (
                id SERIAL PRIMARY KEY,
                guild_id BIGINT NOT NULL,
                category TEXT NOT NULL,
                date TIMESTAMP DEFAULT NOW(),
                remaining INTEGER NOT NULL,
                change INTEGER NOT NULL,
                comment TEXT,
                created_by BIGINT,
                status TEXT DEFAULT 'approved'
            )
        ''')
        
        # Отчёты о мероприятиях
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS event_reports (
                id SERIAL PRIMARY KEY,
                guild_id BIGINT NOT NULL,
                event_type TEXT NOT NULL,
                fields JSONB NOT NULL,
                created_by BIGINT,
                timestamp TIMESTAMP DEFAULT NOW(),
                status TEXT DEFAULT 'approved'
            )
        ''')
        
        # Конкурс инвайтов
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS contest_invites (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                message_id BIGINT NOT NULL,
                channel_id BIGINT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT NOW(),
                reviewed_by BIGINT
            )
        ''')
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS contest_leaderboard (
                user_id BIGINT PRIMARY KEY,
                points INTEGER DEFAULT 0
            )
        ''')
        # Таблица заявок на премию
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS premium_requests (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                contract_type TEXT NOT NULL,
                screenshot_url TEXT,
                status TEXT DEFAULT 'pending',
                requested_at TIMESTAMP DEFAULT NOW(),
                reviewed_by BIGINT,
                reviewed_at TIMESTAMP,
                amount INTEGER,
                paid BOOLEAN DEFAULT FALSE,
                paid_at TIMESTAMP
            )
        ''')

        await conn.execute('''
            CREATE TABLE IF NOT EXISTS inviter_stats (
                user_id BIGINT PRIMARY KEY,
                daily_calls INTEGER DEFAULT 0,
                weekly_calls INTEGER DEFAULT 0,
                total_calls INTEGER DEFAULT 0,
                daily_accepted INTEGER DEFAULT 0,
                weekly_accepted INTEGER DEFAULT 0,
                last_reset_daily DATE,
                last_reset_weekly DATE
            )
        ''')
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS inviter_payments (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                amount INTEGER,
                type TEXT,           -- 'accept' или 'weekly_bonus'
                status TEXT DEFAULT 'unpaid',
                created_at TIMESTAMP DEFAULT NOW(),
                paid_at TIMESTAMP
            )
        ''')
    
    print("✅ База данных PostgreSQL инициализирована")

async def close_db():
    """Закрытие пула соединений."""
    global _pool
    if _pool:
        await _pool.close()
        print("🔌 Пул соединений PostgreSQL закрыт")

# ---------- Вспомогательные функции ----------
async def fetch_one(query: str, *args) -> Optional[asyncpg.Record]:
    async with _pool.acquire() as conn:
        return await conn.fetchrow(query, *args)

async def fetch_all(query: str, *args) -> List[asyncpg.Record]:
    async with _pool.acquire() as conn:
        return await conn.fetch(query, *args)

async def execute(query: str, *args) -> str:
    async with _pool.acquire() as conn:
        return await conn.execute(query, *args)

# ---------- Чёрный список ----------
async def is_blacklisted(user_id: int) -> Optional[str]:
    row = await fetch_one("SELECT reason FROM blacklist WHERE user_id = $1", user_id)
    return row['reason'] if row else None

async def add_to_blacklist(user_id: int, reason: str, moderator_id: int):
    await execute(
        "INSERT INTO blacklist (user_id, reason, date, moderator_id) VALUES ($1, $2, $3, $4) "
        "ON CONFLICT (user_id) DO UPDATE SET reason = EXCLUDED.reason, date = EXCLUDED.date, moderator_id = EXCLUDED.moderator_id",
        user_id, reason, datetime.now(), moderator_id
    )

async def remove_from_blacklist(user_id: int):
    await execute("DELETE FROM blacklist WHERE user_id = $1", user_id)

async def get_all_blacklisted():
    return await fetch_all("SELECT user_id, reason, date, moderator_id FROM blacklist ORDER BY date DESC")

# ---------- Заявки ----------
async def add_application(user_id: int, answers_json: str, message_id: int, ping_message_id: int = None) -> int:
    row = await fetch_one(
        "INSERT INTO applications (user_id, answers, message_id, ping_message_id) VALUES ($1, $2, $3, $4) RETURNING id",
        user_id, answers_json, message_id, ping_message_id
    )
    return row['id']

async def get_application(app_id: int):
    return await fetch_one(
        "SELECT user_id, answers, status, reviewer_id, message_id, date, claimed_by, ping_message_id FROM applications WHERE id = $1",
        app_id
    )

async def get_application_by_message(message_id: int):
    return await fetch_one(
        "SELECT id, user_id, answers, status, reviewer_id, message_id, claimed_by, ping_message_id FROM applications WHERE message_id = $1",
        message_id
    )

async def update_application_status(app_id: int, status: str, reviewer_id: int):
    await execute("UPDATE applications SET status = $1, reviewer_id = $2 WHERE id = $3", status, reviewer_id, app_id)

async def set_application_claimed(app_id: int, claimed_by: int):
    await execute("UPDATE applications SET claimed_by = $1 WHERE id = $2", claimed_by, app_id)

async def get_application_claimed(app_id: int):
    row = await fetch_one("SELECT claimed_by FROM applications WHERE id = $1", app_id)
    return row['claimed_by'] if row else None

async def set_application_ping_message(app_id: int, ping_msg_id: int):
    await execute("UPDATE applications SET ping_message_id = $1 WHERE id = $2", ping_msg_id, app_id)

async def get_user_applications(user_id: int):
    return await fetch_all(
        "SELECT id, status, date, message_id FROM applications WHERE user_id = $1 ORDER BY date DESC",
        user_id
    )

async def get_all_applications(limit: int = 50):
    return await fetch_all(
        "SELECT id, user_id, status, date FROM applications ORDER BY date DESC LIMIT $1",
        limit
    )

# ---------- Настройки ----------
async def are_applications_open() -> bool:
    row = await fetch_one("SELECT value FROM settings WHERE key = 'applications_open'")
    return row['value'] == 'true' if row else True

async def set_applications_open(value: bool):
    await execute("UPDATE settings SET value = $1 WHERE key = 'applications_open'", 'true' if value else 'false')

# ---------- Портфели ----------
async def create_portfolio(channel_id: int, owner_id: int, rank: str, tier: int = 0,
                          pinned_by: int = None, thread_rp_id: int = None, thread_gang_id: int = None):
    await execute(
        "INSERT INTO portfolios (channel_id, owner_id, rank, tier, pinned_by, thread_rp_id, thread_gang_id, created_at) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7, $8)",
        channel_id, owner_id, rank, tier, pinned_by, thread_rp_id, thread_gang_id, datetime.now()
    )

async def get_portfolio_by_owner(owner_id: int):
    return await fetch_one(
        "SELECT channel_id, rank, tier, pinned_by, thread_rp_id, thread_gang_id FROM portfolios WHERE owner_id = $1",
        owner_id
    )

async def get_portfolio_by_channel(channel_id: int):
    return await fetch_one(
        "SELECT owner_id, rank, tier, pinned_by, thread_rp_id, thread_gang_id FROM portfolios WHERE channel_id = $1",
        channel_id
    )

async def get_all_portfolios():
    return await fetch_all(
        "SELECT channel_id, owner_id, rank, tier, pinned_by, thread_rp_id, thread_gang_id, created_at FROM portfolios"
    )

async def update_portfolio_rank(channel_id: int, new_rank: str):
    await execute("UPDATE portfolios SET rank = $1 WHERE channel_id = $2", new_rank, channel_id)

async def update_portfolio_tier(channel_id: int, new_tier: int):
    await execute("UPDATE portfolios SET tier = $1 WHERE channel_id = $2", new_tier, channel_id)

async def update_portfolio_pinned(channel_id: int, pinned_by: int):
    await execute("UPDATE portfolios SET pinned_by = $1 WHERE channel_id = $2", pinned_by, channel_id)

async def delete_portfolio(channel_id: int):
    await execute("DELETE FROM portfolios WHERE channel_id = $1", channel_id)

# ---------- AFK ----------
async def add_afk(user_id: int, start_time: float, duration_seconds: int, reason: str, channel_id: int = None):
    await execute(
        "INSERT INTO afk (user_id, start_time, duration_seconds, reason, channel_id) VALUES ($1, $2, $3, $4, $5) "
        "ON CONFLICT (user_id) DO UPDATE SET start_time = EXCLUDED.start_time, duration_seconds = EXCLUDED.duration_seconds, "
        "reason = EXCLUDED.reason, channel_id = EXCLUDED.channel_id, notified_expired = 0",
        user_id, start_time, duration_seconds, reason, channel_id
    )

async def remove_afk(user_id: int):
    await execute("DELETE FROM afk WHERE user_id = $1", user_id)

async def get_afk(user_id: int):
    return await fetch_one("SELECT start_time, duration_seconds, reason FROM afk WHERE user_id = $1", user_id)

async def is_afk(user_id: int) -> bool:
    row = await fetch_one("SELECT 1 FROM afk WHERE user_id = $1", user_id)
    return row is not None

async def get_all_afk():
    return await fetch_all("SELECT user_id, start_time, duration_seconds, reason FROM afk")

async def mark_afk_notified(user_id: int):
    await execute("UPDATE afk SET notified_expired = 1 WHERE user_id = $1", user_id)

async def get_afk_to_notify():
    now = datetime.now().timestamp()
    rows = await fetch_all("SELECT user_id FROM afk WHERE start_time + duration_seconds <= $1 AND notified_expired = 0", now)
    return [r['user_id'] for r in rows]

# ---------- Отпуска ----------
async def add_vacation(user_id: int, start_time: float, duration_text: str, reason: str, channel_id: int = None):
    await execute(
        "INSERT INTO vacations (user_id, start_time, duration_text, reason, channel_id) VALUES ($1, $2, $3, $4, $5) "
        "ON CONFLICT (user_id) DO UPDATE SET start_time = EXCLUDED.start_time, duration_text = EXCLUDED.duration_text, "
        "reason = EXCLUDED.reason, channel_id = EXCLUDED.channel_id",
        user_id, start_time, duration_text, reason, channel_id
    )

async def remove_vacation(user_id: int):
    await execute("DELETE FROM vacations WHERE user_id = $1", user_id)

async def get_vacation(user_id: int):
    return await fetch_one("SELECT start_time, duration_text, reason FROM vacations WHERE user_id = $1", user_id)

async def is_on_vacation(user_id: int) -> bool:
    row = await fetch_one("SELECT 1 FROM vacations WHERE user_id = $1", user_id)
    return row is not None

async def get_all_vacations():
    return await fetch_all("SELECT user_id, start_time, duration_text, reason FROM vacations")

# ---------- Статистика игроков ----------
async def create_or_update_player_stats(user_id: int, accepted_by: int = None, accepted_date = None,
                                        warns: int = None, points: int = None, voice_time: int = None):
    await execute("""
        INSERT INTO player_stats (user_id, accepted_by, accepted_date, warns, points, voice_time, last_updated)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        ON CONFLICT (user_id) DO UPDATE SET
            accepted_by = COALESCE(EXCLUDED.accepted_by, player_stats.accepted_by),
            accepted_date = COALESCE(EXCLUDED.accepted_date, player_stats.accepted_date),
            warns = COALESCE(EXCLUDED.warns, player_stats.warns),
            points = COALESCE(EXCLUDED.points, player_stats.points),
            voice_time = COALESCE(EXCLUDED.voice_time, player_stats.voice_time),
            last_updated = EXCLUDED.last_updated
    """, user_id, accepted_by, accepted_date, warns or 0, points or 0, voice_time or 0, datetime.now())

async def get_player_stats(user_id: int):
    return await fetch_one("SELECT accepted_by, accepted_date, warns, points, voice_time FROM player_stats WHERE user_id = $1", user_id)

# ---------- Запросы грина ----------
async def add_green_request(user_id: int, amount: int, level: int, channel_id: int) -> int:
    row = await fetch_one(
        "INSERT INTO green_requests (user_id, amount, level, channel_id) VALUES ($1, $2, $3, $4) RETURNING id",
        user_id, amount, level, channel_id
    )
    return row['id']

async def update_green_request_message(req_id: int, message_id: int):
    await execute("UPDATE green_requests SET message_id = $1 WHERE id = $2", message_id, req_id)

async def update_green_request_thread(req_id: int, thread_id: int):
    await execute("UPDATE green_requests SET thread_id = $1 WHERE id = $2", thread_id, req_id)

async def update_green_request_status(req_id: int, status: str, granted_by: int):
    await execute("UPDATE green_requests SET status = $1, granted_by = $2, granted_at = $3 WHERE id = $4",
                  status, granted_by, datetime.now(), req_id)

async def get_green_request(req_id: int):
    return await fetch_one("SELECT user_id, amount, level, status FROM green_requests WHERE id = $1", req_id)

# ---------- Мероприятия ----------
async def add_event(message_id_info: int, message_id_main: int, message_id_sub: int, channel_id: int,
                    creator_id: int, event_type: str, title: str, server: str, time: str, map_name: str,
                    limit_num: int, group_name: str) -> int:
    row = await fetch_one("""
        INSERT INTO events (message_id_info, message_id_main, message_id_sub, channel_id, creator_id, type, title, server, time, map, "limit", group_name)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12) RETURNING id
    """, message_id_info, message_id_main, message_id_sub, channel_id, creator_id, event_type, title, server, time, map_name, limit_num, group_name)
    return row['id']

async def get_event_by_message(message_id: int):
    return await fetch_one("""
        SELECT id, creator_id, type, title, server, time, map, "limit", group_name, is_open,
               message_id_info, message_id_main, message_id_sub, channel_id
        FROM events WHERE message_id_info = $1 OR message_id_main = $1 OR message_id_sub = $1
    """, message_id)

async def get_event_by_info_message(message_id_info: int):
    return await fetch_one("""
        SELECT id, creator_id, type, title, server, time, map, "limit", group_name, is_open,
               message_id_info, message_id_main, message_id_sub, channel_id
        FROM events WHERE message_id_info = $1
    """, message_id_info)

async def update_event(event_id: int, **kwargs):
    if not kwargs:
        return
    set_clause = []
    values = []
    for key, value in kwargs.items():
        if value is not None:
            set_clause.append(f"{key} = ${len(values)+1}")
            values.append(value)
    values.append(event_id)
    query = f"UPDATE events SET {', '.join(set_clause)} WHERE id = ${len(values)}"
    await execute(query, *values)

async def update_event_messages(event_id: int, message_id_info: int = None,
                                message_id_main: int = None, message_id_sub: int = None):
    updates = {}
    if message_id_info is not None:
        updates['message_id_info'] = message_id_info
    if message_id_main is not None:
        updates['message_id_main'] = message_id_main
    if message_id_sub is not None:
        updates['message_id_sub'] = message_id_sub
    if updates:
        await update_event(event_id, **updates)

async def add_participant(event_id: int, user_id: int, role: str) -> bool:
    exists = await fetch_one("SELECT 1 FROM event_participants WHERE event_id = $1 AND user_id = $2", event_id, user_id)
    if exists:
        return False
    await execute("INSERT INTO event_participants (event_id, user_id, role) VALUES ($1, $2, $3)", event_id, user_id, role)
    return True

async def remove_participant(event_id: int, user_id: int):
    await execute("DELETE FROM event_participants WHERE event_id = $1 AND user_id = $2", event_id, user_id)

async def get_participants(event_id: int, role: str = None):
    if role:
        rows = await fetch_all("SELECT user_id FROM event_participants WHERE event_id = $1 AND role = $2", event_id, role)
        return [r['user_id'] for r in rows]
    else:
        rows = await fetch_all("SELECT user_id, role FROM event_participants WHERE event_id = $1", event_id)
        return rows

async def count_participants(event_id: int, role: str) -> int:
    row = await fetch_one("SELECT COUNT(*) FROM event_participants WHERE event_id = $1 AND role = $2", event_id, role)
    return row['count']

async def clear_participants(event_id: int, role: str = None):
    if role:
        await execute("DELETE FROM event_participants WHERE event_id = $1 AND role = $2", event_id, role)
    else:
        await execute("DELETE FROM event_participants WHERE event_id = $1", event_id)

async def delete_event(event_id: int):
    async with _pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("DELETE FROM event_participants WHERE event_id = $1", event_id)
            await conn.execute("DELETE FROM events WHERE id = $1", event_id)

# ---------- Логи ----------
async def add_log(guild_id: int, user_id: int, action_type: str, details: str = None):
    await execute(
        "INSERT INTO logs (guild_id, user_id, action_type, details) VALUES ($1, $2, $3, $4)",
        guild_id, user_id, action_type, details
    )

async def search_logs(guild_id: int, user_id: int = None, action_type: str = None,
                      start_date: str = None, end_date: str = None, limit: int = 100):
    query = "SELECT id, user_id, action_type, details, timestamp FROM logs WHERE guild_id = $1"
    params = [guild_id]
    idx = 2
    if user_id is not None:
        query += f" AND user_id = ${idx}"
        params.append(user_id)
        idx += 1
    if action_type is not None:
        query += f" AND action_type = ${idx}"
        params.append(action_type)
        idx += 1
    if start_date is not None:
        query += f" AND timestamp >= ${idx}"
        params.append(start_date)
        idx += 1
    if end_date is not None:
        query += f" AND timestamp <= ${idx}"
        params.append(end_date)
        idx += 1
    query += f" ORDER BY timestamp DESC LIMIT ${idx}"
    params.append(limit)
    return await fetch_all(query, *params)

# ---------- Кики ----------
async def add_kick(guild_id: int, moderator_id: int, user_id: int, reason: str,
                   kick_type: str = "discord", static: str = None):
    await execute(
        "INSERT INTO kicks (guild_id, moderator_id, user_id, reason, kick_type, static) VALUES ($1, $2, $3, $4, $5, $6)",
        guild_id, moderator_id, user_id, reason, kick_type, static
    )

async def get_kicks(guild_id: int, limit: int = 50):
    return await fetch_all(
        "SELECT id, moderator_id, user_id, reason, kick_type, static, timestamp FROM kicks WHERE guild_id = $1 ORDER BY timestamp DESC LIMIT $2",
        guild_id, limit
    )

async def get_last_kick_id(guild_id: int) -> int:
    row = await fetch_one("SELECT id FROM kicks WHERE guild_id = $1 ORDER BY id DESC LIMIT 1", guild_id)
    return row['id'] if row else 0

# ---------- Оружие ----------
async def get_current_weapons(guild_id: int) -> Dict[str, int]:
    rows = await fetch_all("""
        SELECT category, remaining FROM weapons w1
        WHERE guild_id = $1 AND status = 'approved'
        AND id = (SELECT id FROM weapons w2
                  WHERE w2.guild_id = w1.guild_id AND w2.category = w1.category
                  ORDER BY w2.id DESC LIMIT 1)
    """, guild_id)
    return {r['category']: r['remaining'] for r in rows}

async def get_last_weapon_change(guild_id: int, category: str) -> int:
    row = await fetch_one("""
        SELECT change FROM weapons
        WHERE guild_id = $1 AND category = $2 AND status = 'approved'
        ORDER BY date DESC LIMIT 1
    """, guild_id, category)
    return row['change'] if row else 0

async def update_weapon_stock(guild_id: int, category: str, remaining: int, change: int,
                              comment: str, created_by: int):
    await execute(
        "INSERT INTO weapons (guild_id, category, remaining, change, comment, created_by) VALUES ($1, $2, $3, $4, $5, $6)",
        guild_id, category, remaining, change, comment, created_by
    )

async def get_weapons_history(guild_id: int, category: str = None, limit: int = 20):
    if category:
        return await fetch_all(
            "SELECT date, category, remaining, change, comment, created_by FROM weapons WHERE guild_id = $1 AND category = $2 ORDER BY date DESC LIMIT $3",
            guild_id, category, limit
        )
    else:
        return await fetch_all(
            "SELECT date, category, remaining, change, comment, created_by FROM weapons WHERE guild_id = $1 ORDER BY date DESC LIMIT $2",
            guild_id, limit
        )

async def get_last_weapon_id(guild_id: int) -> int:
    row = await fetch_one("SELECT id FROM weapons WHERE guild_id = $1 ORDER BY id DESC LIMIT 1", guild_id)
    return row['id'] if row else 0

# ---------- Отчёты о мероприятиях ----------
async def add_event_report(guild_id: int, event_type: str, fields: dict, created_by: int):
    await execute(
        "INSERT INTO event_reports (guild_id, event_type, fields, created_by) VALUES ($1, $2, $3, $4)",
        guild_id, event_type, json.dumps(fields, ensure_ascii=False), created_by
    )

async def get_last_event_report_id(guild_id: int) -> int:
    row = await fetch_one("SELECT id FROM event_reports WHERE guild_id = $1 ORDER BY id DESC LIMIT 1", guild_id)
    return row['id'] if row else 0

# ---------- Конкурс инвайтов ----------
async def add_invite_submission(user_id: int, message_id: int, channel_id: int):
    await execute(
        "INSERT INTO contest_invites (user_id, message_id, channel_id) VALUES ($1, $2, $3)",
        user_id, message_id, channel_id
    )

async def approve_invite(invite_id: int, reviewer_id: int):
    async with _pool.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow("SELECT user_id FROM contest_invites WHERE id = $1", invite_id)
            if not row:
                return
            user_id = row['user_id']
            await conn.execute("UPDATE contest_invites SET status = 'approved', reviewed_by = $1 WHERE id = $2", reviewer_id, invite_id)
            await conn.execute("INSERT INTO contest_leaderboard (user_id, points) VALUES ($1, 1) ON CONFLICT (user_id) DO UPDATE SET points = contest_leaderboard.points + 1", user_id)

async def reject_invite(invite_id: int, reviewer_id: int):
    await execute("UPDATE contest_invites SET status = 'rejected', reviewed_by = $1 WHERE id = $2", reviewer_id, invite_id)

async def get_leaderboard(limit: int = 10):
    return await fetch_all("SELECT user_id, points FROM contest_leaderboard ORDER BY points DESC LIMIT $1", limit)

async def get_invite_by_message(message_id: int):
    row = await fetch_one("SELECT id FROM contest_invites WHERE message_id = $1", message_id)
    return row['id'] if row else None

async def reset_leaderboard():
    await execute("DELETE FROM contest_leaderboard")

# ---------- Премии ----------
async def add_premium_request(user_id: int, contract_type: str, screenshot_url: str = None) -> int:
    row = await fetch_one(
        "INSERT INTO premium_requests (user_id, contract_type, screenshot_url) VALUES ($1, $2, $3) RETURNING id",
        user_id, contract_type, screenshot_url
    )
    return row['id']

async def get_premium_request(req_id: int):
    return await fetch_one(
        "SELECT id, user_id, contract_type, screenshot_url, status, amount, paid FROM premium_requests WHERE id = $1",
        req_id
    )

async def update_premium_request_status(req_id: int, status: str, reviewer_id: int):
    await execute(
        "UPDATE premium_requests SET status = $1, reviewed_by = $2, reviewed_at = NOW() WHERE id = $3",
        status, reviewer_id, req_id
    )

async def set_premium_amount(req_id: int, amount: int):
    await execute("UPDATE premium_requests SET amount = $1 WHERE id = $2", amount, req_id)

async def get_pending_premium_requests(limit: int = 50):
    return await fetch_all(
        "SELECT id, user_id, contract_type, screenshot_url, requested_at FROM premium_requests WHERE status = 'pending' ORDER BY requested_at ASC LIMIT $1",
        limit
    )

async def get_approved_unpaid_requests():
    return await fetch_all(
        "SELECT user_id, amount FROM premium_requests WHERE status = 'approved' AND paid = FALSE"
    )

async def mark_premiums_as_paid(user_ids: list = None):
    if user_ids:
        await execute(
            "UPDATE premium_requests SET paid = TRUE, paid_at = NOW() WHERE status = 'approved' AND paid = FALSE AND user_id = ANY($1)",
            user_ids
        )
    else:
        await execute(
            "UPDATE premium_requests SET paid = TRUE, paid_at = NOW() WHERE status = 'approved' AND paid = FALSE"
        )

import json
from config import DEFAULT_SETTINGS

settings_cache = {}

async def load_all_settings():
    """Загружает все настройки из БД в глобальный кэш."""
    global settings_cache
    rows = await fetch_all("SELECT key, value FROM settings")
    for row in rows:
        key = row['key']
        value = row['value']
        # Приведение типа на основе DEFAULT_SETTINGS
        if key in DEFAULT_SETTINGS:
            default_val = DEFAULT_SETTINGS[key]
            if isinstance(default_val, bool):
                value = value.lower() == 'true'
            elif isinstance(default_val, int):
                value = int(value)
            elif isinstance(default_val, list):
                value = json.loads(value)
        settings_cache[key] = value
    # Добавляем отсутствующие ключи из DEFAULT_SETTINGS
    for key, default_val in DEFAULT_SETTINGS.items():
        if key not in settings_cache:
            settings_cache[key] = default_val

def get_setting(key, default=None):
    return settings_cache.get(key, default)

async def set_setting(key: str, value):
    """Сохраняет настройку в БД и обновляет кэш."""
    # Преобразуем значение в строку
    if isinstance(value, bool):
        str_value = 'true' if value else 'false'
    elif isinstance(value, list) or isinstance(value, dict):
        str_value = json.dumps(value, ensure_ascii=False)
    else:
        str_value = str(value)
    await execute(
        "INSERT INTO settings (key, value) VALUES ($1, $2) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
        key, str_value
    )
    # Обновляем кэш с приведением типа
    if key in DEFAULT_SETTINGS:
        default_val = DEFAULT_SETTINGS[key]
        if isinstance(default_val, bool):
            value = str_value.lower() == 'true'
        elif isinstance(default_val, int):
            value = int(str_value)
        elif isinstance(default_val, list):
            value = json.loads(str_value)
    settings_cache[key] = value

async def reset_setting(key: str):
    """Сбрасывает настройку к значению по умолчанию из config."""
    await execute("DELETE FROM settings WHERE key = $1", key)
    if key in DEFAULT_SETTINGS:
        settings_cache[key] = DEFAULT_SETTINGS[key]
    elif key in settings_cache:
        del settings_cache[key]

async def init_settings():
    """Заполняет таблицу settings значениями по умолчанию, если они отсутствуют."""
    for key, default_val in DEFAULT_SETTINGS.items():
        # Преобразуем в строку
        if isinstance(default_val, bool):
            str_val = 'true' if default_val else 'false'
        elif isinstance(default_val, list) or isinstance(default_val, dict):
            str_val = json.dumps(default_val, ensure_ascii=False)
        else:
            str_val = str(default_val)
        await execute(
            "INSERT INTO settings (key, value) VALUES ($1, $2) ON CONFLICT (key) DO NOTHING",
            key, str_val
        )


async def update_inviter_calls(user_id: int, action: str):
    """Увеличивает счётчики обзвонов (accept/reject)."""
    today = datetime.now().date()
    # Убедимся, что запись существует
    await execute('''
        INSERT INTO inviter_stats (user_id, daily_calls, weekly_calls, total_calls, daily_accepted, last_reset_daily, last_reset_weekly)
        VALUES ($1, 0, 0, 0, 0, $2, $2)
        ON CONFLICT (user_id) DO NOTHING
    ''', user_id, today)
    if action == 'accept':
        await execute('UPDATE inviter_stats SET daily_calls = daily_calls + 1, weekly_calls = weekly_calls + 1, total_calls = total_calls + 1, daily_accepted = daily_accepted + 1, weekly_accepted = COALESCE(weekly_accepted,0) + 1 WHERE user_id = $1', user_id)
    else:  # reject
        await execute('UPDATE inviter_stats SET daily_calls = daily_calls + 1, weekly_calls = weekly_calls + 1, total_calls = total_calls + 1 WHERE user_id = $1', user_id)

async def get_inviter_stats(user_id: int):
    return await fetch_one('SELECT * FROM inviter_stats WHERE user_id = $1', user_id)

async def get_inviter_leaderboard_daily(limit=10):
    return await fetch_all('SELECT user_id, daily_calls, daily_accepted FROM inviter_stats ORDER BY daily_calls DESC LIMIT $1', limit)

async def get_inviter_leaderboard_weekly(limit=10):
    return await fetch_all('SELECT user_id, weekly_calls FROM inviter_stats ORDER BY weekly_calls DESC LIMIT $1', limit)

async def get_inviter_leaderboard_total(limit=10):
    return await fetch_all('SELECT user_id, total_calls FROM inviter_stats ORDER BY total_calls DESC LIMIT $1', limit)

async def get_daily_payment_list():
    """Возвращает список (user_id, daily_calls) для всех, у кого daily_calls > 0."""
    return await fetch_all('SELECT user_id, daily_calls FROM inviter_stats WHERE daily_calls > 0')

async def add_inviter_payment(user_id: int, amount: int, pay_type: str):
    await execute('INSERT INTO inviter_payments (user_id, amount, type, status) VALUES ($1, $2, $3, \'unpaid\')', user_id, amount, pay_type)

async def mark_daily_payments_paid():
    """Помечает все unpaid платежи за сегодня как paid."""
    await execute('UPDATE inviter_payments SET status = \'paid\', paid_at = NOW() WHERE status = \'unpaid\' AND date_trunc(\'day\', created_at) = CURRENT_DATE')

async def reset_daily_stats():
    await execute('UPDATE inviter_stats SET daily_calls = 0, daily_accepted = 0, last_reset_daily = CURRENT_DATE WHERE last_reset_daily IS NULL OR last_reset_daily < CURRENT_DATE')

async def reset_weekly_stats():
    await execute('UPDATE inviter_stats SET weekly_calls = 0, weekly_accepted = 0, last_reset_weekly = CURRENT_DATE WHERE last_reset_weekly IS NULL OR last_reset_weekly < CURRENT_DATE - INTERVAL \'7 days\'')

async def reset_daily_accepted():
    """Обнуляет daily_accepted и daily_calls у всех инвайтеров (после выплаты)."""
    await execute('UPDATE inviter_stats SET daily_accepted = 0, daily_calls = 0 WHERE daily_accepted > 0 OR daily_calls > 0')