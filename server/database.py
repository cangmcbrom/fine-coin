"""
FINE COIN - Database Module
Uses SQLite for simple, file-based storage.
"""

import sqlite3
import os
import time
import threading

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'fine_coin.db')

# Thread-local storage for connections
_local = threading.local()


def get_connection():
    """Get a thread-local database connection."""
    if not hasattr(_local, 'connection') or _local.connection is None:
        _local.connection = sqlite3.connect(DB_PATH)
        _local.connection.row_factory = sqlite3.Row
        _local.connection.execute("PRAGMA journal_mode=WAL")
        _local.connection.execute("PRAGMA foreign_keys=ON")
    return _local.connection


def init_db():
    """Initialize database schema."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            username TEXT DEFAULT '',
            first_name TEXT DEFAULT '',
            balance REAL DEFAULT 0.0,
            tap_power_level INTEGER DEFAULT 1,
            max_energy_level INTEGER DEFAULT 1,
            recharge_rate_level INTEGER DEFAULT 1,
            current_energy INTEGER DEFAULT 1000,
            last_energy_update REAL DEFAULT 0,
            unlimited_energy_until REAL DEFAULT 0,
            referral_code TEXT UNIQUE,
            referred_by INTEGER DEFAULT NULL,
            total_taps INTEGER DEFAULT 0,
            last_tap_time REAL DEFAULT 0,
            tap_burst_count INTEGER DEFAULT 0,
            is_banned INTEGER DEFAULT 0,
            created_at REAL DEFAULT 0,
            updated_at REAL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER NOT NULL,
            referred_id INTEGER NOT NULL,
            bonus_amount REAL DEFAULT 50.0,
            created_at REAL DEFAULT 0,
            FOREIGN KEY (referrer_id) REFERENCES users(telegram_id),
            FOREIGN KEY (referred_id) REFERENCES users(telegram_id)
        );

        CREATE TABLE IF NOT EXISTS star_purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            package_type TEXT NOT NULL,
            stars_spent INTEGER NOT NULL,
            duration_minutes INTEGER NOT NULL,
            purchased_at REAL DEFAULT 0,
            expires_at REAL DEFAULT 0,
            FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
        );

        CREATE TABLE IF NOT EXISTS upgrade_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            upgrade_type TEXT NOT NULL,
            from_level INTEGER NOT NULL,
            to_level INTEGER NOT NULL,
            cost REAL NOT NULL,
            purchased_at REAL DEFAULT 0,
            FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
        );
    ''')

    conn.commit()
    print("[DB] Database initialized successfully.")


def get_user(telegram_id):
    """Get user by telegram_id."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    row = cursor.fetchone()
    if row:
        return dict(row)
    return None


def create_user(telegram_id, username='', first_name='', referral_code=None, referred_by=None):
    """Create a new user."""
    conn = get_connection()
    cursor = conn.cursor()
    now = time.time()

    if not referral_code:
        referral_code = f"FINE{telegram_id}"

    try:
        cursor.execute('''
            INSERT INTO users (telegram_id, username, first_name, balance, 
                             current_energy, last_energy_update, referral_code, 
                             referred_by, created_at, updated_at)
            VALUES (?, ?, ?, 0.0, 1000, ?, ?, ?, ?, ?)
        ''', (telegram_id, username, first_name, now, referral_code, referred_by, now, now))
        conn.commit()
        return get_user(telegram_id)
    except sqlite3.IntegrityError:
        return get_user(telegram_id)


def update_user(telegram_id, **kwargs):
    """Update user fields."""
    conn = get_connection()
    cursor = conn.cursor()
    kwargs['updated_at'] = time.time()

    set_clause = ', '.join(f"{k} = ?" for k in kwargs.keys())
    values = list(kwargs.values()) + [telegram_id]

    cursor.execute(f"UPDATE users SET {set_clause} WHERE telegram_id = ?", values)
    conn.commit()
    return get_user(telegram_id)


def get_tap_power(level):
    """Calculate tap power based on level. Level 1 = 0.2, Level 2 = 0.4, etc."""
    return round(0.2 * level, 1)


def get_max_energy(level):
    """Calculate max energy based on level. Level 1 = 1000, Level 2 = 1500, etc."""
    return 1000 + (level - 1) * 500


def get_recharge_rate(level):
    """Calculate recharge rate (per minute) based on level. Level 1 = 10, Level 2 = 15, etc."""
    return 10 + (level - 1) * 5


def get_upgrade_cost(upgrade_type, current_level):
    """Calculate upgrade cost. Cost increases exponentially."""
    base_costs = {
        'tap_power': 50,
        'max_energy': 75,
        'recharge_rate': 100
    }
    base = base_costs.get(upgrade_type, 50)
    return round(base * (1.8 ** (current_level - 1)), 1)


def process_tap(telegram_id, tap_count=1):
    """
    Process a tap action. Returns the result.
    Anti-cheat: max 20 taps per request, rate limit checked.
    """
    user = get_user(telegram_id)
    if not user:
        return {'error': 'User not found'}

    if user['is_banned']:
        return {'error': 'User is banned'}

    # Anti-cheat: limit taps per request
    tap_count = min(tap_count, 20)
    tap_count = max(tap_count, 1)

    now = time.time()

    # Anti-cheat: check tap speed (max ~15 taps per second)
    time_since_last = now - user['last_tap_time'] if user['last_tap_time'] else 1.0
    if time_since_last < 0.05:  # Too fast
        burst = user['tap_burst_count'] + 1
        if burst > 50:
            update_user(telegram_id, is_banned=1)
            return {'error': 'Banned for botting'}
        update_user(telegram_id, tap_burst_count=burst)
        return {'error': 'Too fast', 'warning': True}
    elif time_since_last > 2.0:
        update_user(telegram_id, tap_burst_count=0)

    # Calculate current energy (with regeneration)
    current_energy = calculate_current_energy(user, now)

    # Check unlimited energy
    has_unlimited = user['unlimited_energy_until'] > now

    if not has_unlimited and current_energy < tap_count:
        tap_count = int(current_energy)
        if tap_count <= 0:
            return {'error': 'No energy', 'current_energy': 0}

    # Calculate reward
    tap_power = get_tap_power(user['tap_power_level'])
    reward = round(tap_power * tap_count, 2)

    # Update energy
    if not has_unlimited:
        new_energy = max(0, current_energy - tap_count)
    else:
        new_energy = get_max_energy(user['max_energy_level'])

    # Update user
    new_balance = round(user['balance'] + reward, 2)
    update_user(
        telegram_id,
        balance=new_balance,
        current_energy=int(new_energy),
        last_energy_update=now,
        last_tap_time=now,
        total_taps=user['total_taps'] + tap_count
    )

    max_energy = get_max_energy(user['max_energy_level'])

    return {
        'success': True,
        'reward': reward,
        'tap_power': tap_power,
        'new_balance': new_balance,
        'current_energy': int(new_energy) if not has_unlimited else max_energy,
        'max_energy': max_energy,
        'has_unlimited': has_unlimited,
        'taps_processed': tap_count
    }


def calculate_current_energy(user, now=None):
    """Calculate current energy considering regeneration."""
    if now is None:
        now = time.time()

    # If unlimited energy is active
    if user['unlimited_energy_until'] > now:
        return get_max_energy(user['max_energy_level'])

    time_elapsed = now - user['last_energy_update']
    minutes_elapsed = time_elapsed / 60.0
    recharge_rate = get_recharge_rate(user['recharge_rate_level'])
    max_energy = get_max_energy(user['max_energy_level'])

    regenerated = minutes_elapsed * recharge_rate
    current = min(max_energy, user['current_energy'] + regenerated)

    return current


def process_upgrade(telegram_id, upgrade_type):
    """Process an upgrade purchase."""
    user = get_user(telegram_id)
    if not user:
        return {'error': 'User not found'}

    level_map = {
        'tap_power': 'tap_power_level',
        'max_energy': 'max_energy_level',
        'recharge_rate': 'recharge_rate_level'
    }

    if upgrade_type not in level_map:
        return {'error': 'Invalid upgrade type'}

    current_level = user[level_map[upgrade_type]]
    max_level = 20  # Max upgrade level

    if current_level >= max_level:
        return {'error': 'Max level reached'}

    cost = get_upgrade_cost(upgrade_type, current_level)

    if user['balance'] < cost:
        return {'error': 'Insufficient balance', 'cost': cost, 'balance': user['balance']}

    # Process purchase
    new_balance = round(user['balance'] - cost, 2)
    new_level = current_level + 1

    conn = get_connection()
    cursor = conn.cursor()
    now = time.time()

    # Record upgrade
    cursor.execute('''
        INSERT INTO upgrade_history (telegram_id, upgrade_type, from_level, to_level, cost, purchased_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (telegram_id, upgrade_type, current_level, new_level, cost, now))

    conn.commit()

    update_data = {
        level_map[upgrade_type]: new_level,
        'balance': new_balance
    }

    # If upgrading max energy, also update current energy to new max
    if upgrade_type == 'max_energy':
        new_max = get_max_energy(new_level)
        update_data['current_energy'] = new_max

    update_user(telegram_id, **update_data)

    next_cost = get_upgrade_cost(upgrade_type, new_level) if new_level < max_level else None

    return {
        'success': True,
        'upgrade_type': upgrade_type,
        'new_level': new_level,
        'cost': cost,
        'new_balance': new_balance,
        'next_cost': next_cost,
        'max_level_reached': new_level >= max_level
    }


def activate_unlimited_energy(telegram_id, duration_minutes, stars_cost, package_type):
    """Activate unlimited energy for a duration."""
    user = get_user(telegram_id)
    if not user:
        return {'error': 'User not found'}

    now = time.time()
    expires_at = now + (duration_minutes * 60)

    # If already has unlimited, extend
    if user['unlimited_energy_until'] > now:
        expires_at = user['unlimited_energy_until'] + (duration_minutes * 60)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO star_purchases (telegram_id, package_type, stars_spent, duration_minutes, purchased_at, expires_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (telegram_id, package_type, stars_cost, duration_minutes, now, expires_at))

    conn.commit()

    update_user(
        telegram_id,
        unlimited_energy_until=expires_at,
        current_energy=get_max_energy(user['max_energy_level'])
    )

    return {
        'success': True,
        'expires_at': expires_at,
        'duration_minutes': duration_minutes
    }


def process_referral(referrer_code, new_user_id, bonus_amount=50):
    """Process a referral."""
    conn = get_connection()
    cursor = conn.cursor()

    # Find referrer
    cursor.execute("SELECT telegram_id FROM users WHERE referral_code = ?", (referrer_code,))
    row = cursor.fetchone()
    if not row:
        return {'error': 'Invalid referral code'}

    referrer_id = row['telegram_id']
    if referrer_id == new_user_id:
        return {'error': 'Cannot refer yourself'}

    # Check if already referred
    cursor.execute("SELECT id FROM referrals WHERE referred_id = ?", (new_user_id,))
    if cursor.fetchone():
        return {'error': 'Already referred'}

    now = time.time()

    # Record referral
    cursor.execute('''
        INSERT INTO referrals (referrer_id, referred_id, bonus_amount, created_at)
        VALUES (?, ?, ?, ?)
    ''', (referrer_id, new_user_id, bonus_amount, now))

    conn.commit()

    # Give bonus to both
    referrer = get_user(referrer_id)
    referred = get_user(new_user_id)

    if referrer:
        update_user(referrer_id, balance=round(referrer['balance'] + bonus_amount, 2))
    if referred:
        update_user(new_user_id, balance=round(referred['balance'] + bonus_amount, 2))

    return {
        'success': True,
        'referrer_id': referrer_id,
        'bonus': bonus_amount
    }


def get_referral_count(telegram_id):
    """Get number of referrals for a user."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM referrals WHERE referrer_id = ?", (telegram_id,))
    row = cursor.fetchone()
    return row['count'] if row else 0


def get_leaderboard(limit=10):
    """Get top users by balance."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT telegram_id, username, first_name, balance FROM users ORDER BY balance DESC LIMIT ?",
        (limit,)
    )
    return [dict(row) for row in cursor.fetchall()]
