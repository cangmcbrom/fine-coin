"""
FINE COIN - Main Server Application
Flask-based backend for the Telegram Mini App tap-to-earn game.
"""

import os
import sys
import time
import json
import hmac
import hashlib
from urllib.parse import unquote, parse_qs
from functools import wraps

from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.database import (
    init_db, get_user, create_user, update_user,
    process_tap, process_upgrade, activate_unlimited_energy,
    process_referral, get_referral_count, get_leaderboard,
    get_tap_power, get_max_energy, get_recharge_rate, get_upgrade_cost,
    calculate_current_energy
)

load_dotenv()

app = Flask(__name__, static_folder='../public', static_url_path='')
CORS(app)

BOT_TOKEN = os.getenv('BOT_TOKEN', 'test_token')
SECRET_KEY = os.getenv('SECRET_KEY', 'dev_secret_key')
DISTRIBUTION_DATE = os.getenv('DISTRIBUTION_DATE', '2026-05-19')
REFERRAL_BONUS = float(os.getenv('REFERRAL_BONUS', '50'))

app.secret_key = SECRET_KEY


# ===== Telegram Auth Middleware =====

def validate_init_data(init_data_raw):
    """
    Validate Telegram Mini App initData.
    In development mode, skip validation.
    """
    if BOT_TOKEN == 'test_token':
        # Development mode - parse without validation
        try:
            params = parse_qs(init_data_raw)
            if 'user' in params:
                user_data = json.loads(unquote(params['user'][0]))
                return user_data
        except Exception:
            pass
        return None

    try:
        parsed = parse_qs(init_data_raw)
        check_hash = parsed.get('hash', [None])[0]
        if not check_hash:
            return None

        # Build data check string
        data_pairs = []
        for key, value in sorted(parsed.items()):
            if key != 'hash':
                data_pairs.append(f"{key}={value[0]}")
        data_check_string = '\n'.join(data_pairs)

        # Create secret key
        secret = hmac.new(
            b'WebAppData',
            BOT_TOKEN.encode(),
            hashlib.sha256
        ).digest()

        # Verify hash
        calculated_hash = hmac.new(
            secret,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()

        if calculated_hash != check_hash:
            return None

        # Parse user data
        if 'user' in parsed:
            return json.loads(unquote(parsed['user'][0]))

        return None
    except Exception as e:
        print(f"[Auth] Validation error: {e}")
        return None


def require_auth(f):
    """Decorator to require Telegram authentication."""
    @wraps(f)
    def decorated(*args, **kwargs):
        init_data = request.headers.get('X-Telegram-Init-Data', '')

        if not init_data:
            # For development, allow query-based auth
            telegram_id = request.args.get('telegram_id')
            if not telegram_id and request.is_json:
                telegram_id = request.json.get('telegram_id')
            if telegram_id and BOT_TOKEN == 'test_token':
                user = get_user(int(telegram_id))
                if not user:
                    user = create_user(int(telegram_id), 'dev_user', 'Developer')
                request.telegram_user = user
                return f(*args, **kwargs)
            return jsonify({'error': 'Unauthorized'}), 401

        user_data = validate_init_data(init_data)
        if not user_data:
            return jsonify({'error': 'Invalid auth data'}), 401

        telegram_id = user_data.get('id')
        username = user_data.get('username', '')
        first_name = user_data.get('first_name', '')

        user = get_user(telegram_id)
        if not user:
            user = create_user(telegram_id, username, first_name)

        request.telegram_user = user
        return f(*args, **kwargs)

    return decorated


# ===== Rate Limiter =====
_rate_limits = {}


def check_rate_limit(telegram_id, action='tap', max_requests=30, window=1.0):
    """Simple in-memory rate limiter."""
    key = f"{telegram_id}:{action}"
    now = time.time()

    if key not in _rate_limits:
        _rate_limits[key] = []

    # Clean old entries
    _rate_limits[key] = [t for t in _rate_limits[key] if now - t < window]

    if len(_rate_limits[key]) >= max_requests:
        return False

    _rate_limits[key].append(now)
    return True


# ===== Static Files =====

@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/assets/<path:filename>')
def serve_assets(filename):
    return send_from_directory(os.path.join(app.static_folder, 'assets'), filename)


# ===== API Routes =====

@app.route('/api/user/init', methods=['POST'])
@require_auth
def api_user_init():
    """Initialize or get user data."""
    user = request.telegram_user
    telegram_id = user['telegram_id']

    now = time.time()
    current_energy = calculate_current_energy(user, now)
    max_energy = get_max_energy(user['max_energy_level'])

    # Update stored energy
    update_user(telegram_id, current_energy=int(current_energy), last_energy_update=now)

    return jsonify({
        'success': True,
        'user': {
            'telegram_id': telegram_id,
            'username': user['username'],
            'first_name': user['first_name'],
            'balance': user['balance'],
            'current_energy': int(current_energy),
            'max_energy': max_energy,
            'tap_power': get_tap_power(user['tap_power_level']),
            'tap_power_level': user['tap_power_level'],
            'max_energy_level': user['max_energy_level'],
            'recharge_rate_level': user['recharge_rate_level'],
            'recharge_rate': get_recharge_rate(user['recharge_rate_level']),
            'has_unlimited_energy': user['unlimited_energy_until'] > now,
            'unlimited_energy_until': user['unlimited_energy_until'],
            'referral_code': user['referral_code'],
            'referral_count': get_referral_count(telegram_id),
            'total_taps': user['total_taps'],
            'distribution_date': DISTRIBUTION_DATE
        }
    })


@app.route('/api/game/tap', methods=['POST'])
@require_auth
def api_tap():
    """Process tap action."""
    user = request.telegram_user
    telegram_id = user['telegram_id']

    if not check_rate_limit(telegram_id, 'tap', max_requests=25, window=1.0):
        return jsonify({'error': 'Rate limited'}), 429

    data = request.get_json() or {}
    tap_count = min(int(data.get('taps', 1)), 20)

    result = process_tap(telegram_id, tap_count)

    if 'error' in result:
        status = 403 if result['error'] == 'Banned for botting' else 400
        return jsonify(result), status

    return jsonify(result)


@app.route('/api/game/energy', methods=['GET'])
@require_auth
def api_get_energy():
    """Get current energy status."""
    user = request.telegram_user
    now = time.time()
    current_energy = calculate_current_energy(user, now)
    max_energy = get_max_energy(user['max_energy_level'])
    has_unlimited = user['unlimited_energy_until'] > now

    return jsonify({
        'current_energy': int(current_energy) if not has_unlimited else max_energy,
        'max_energy': max_energy,
        'recharge_rate': get_recharge_rate(user['recharge_rate_level']),
        'has_unlimited': has_unlimited,
        'unlimited_until': user['unlimited_energy_until'] if has_unlimited else None
    })


@app.route('/api/upgrades/list', methods=['GET'])
@require_auth
def api_upgrades_list():
    """Get available upgrades."""
    user = request.telegram_user

    upgrades = [
        {
            'type': 'tap_power',
            'name': 'Tap Power',
            'description': 'Increase coins per tap',
            'icon': '⚡',
            'current_level': user['tap_power_level'],
            'max_level': 20,
            'current_value': get_tap_power(user['tap_power_level']),
            'next_value': get_tap_power(user['tap_power_level'] + 1) if user['tap_power_level'] < 20 else None,
            'cost': get_upgrade_cost('tap_power', user['tap_power_level']) if user['tap_power_level'] < 20 else None,
            'can_afford': user['balance'] >= get_upgrade_cost('tap_power', user['tap_power_level']) if user['tap_power_level'] < 20 else False
        },
        {
            'type': 'max_energy',
            'name': 'Max Energy',
            'description': 'Increase energy capacity',
            'icon': '🔋',
            'current_level': user['max_energy_level'],
            'max_level': 20,
            'current_value': get_max_energy(user['max_energy_level']),
            'next_value': get_max_energy(user['max_energy_level'] + 1) if user['max_energy_level'] < 20 else None,
            'cost': get_upgrade_cost('max_energy', user['max_energy_level']) if user['max_energy_level'] < 20 else None,
            'can_afford': user['balance'] >= get_upgrade_cost('max_energy', user['max_energy_level']) if user['max_energy_level'] < 20 else False
        },
        {
            'type': 'recharge_rate',
            'name': 'Energy Recharge',
            'description': 'Faster energy recovery',
            'icon': '🔄',
            'current_level': user['recharge_rate_level'],
            'max_level': 20,
            'current_value': get_recharge_rate(user['recharge_rate_level']),
            'next_value': get_recharge_rate(user['recharge_rate_level'] + 1) if user['recharge_rate_level'] < 20 else None,
            'cost': get_upgrade_cost('recharge_rate', user['recharge_rate_level']) if user['recharge_rate_level'] < 20 else None,
            'can_afford': user['balance'] >= get_upgrade_cost('recharge_rate', user['recharge_rate_level']) if user['recharge_rate_level'] < 20 else False
        }
    ]

    return jsonify({'upgrades': upgrades, 'balance': user['balance']})


@app.route('/api/upgrades/buy', methods=['POST'])
@require_auth
def api_buy_upgrade():
    """Purchase an upgrade."""
    user = request.telegram_user
    data = request.get_json() or {}
    upgrade_type = data.get('type')

    if not upgrade_type:
        return jsonify({'error': 'Missing upgrade type'}), 400

    result = process_upgrade(user['telegram_id'], upgrade_type)

    if 'error' in result:
        return jsonify(result), 400

    return jsonify(result)


@app.route('/api/stars/packages', methods=['GET'])
def api_star_packages():
    """Get available Star packages."""
    packages = [
        {
            'id': 'half_hour',
            'name': '30 Min Unlimited Energy',
            'description': 'Non-stop tapping for 30 minutes!',
            'duration_minutes': 30,
            'stars_cost': 5,
            'icon': '⏱️',
            'popular': False
        },
        {
            'id': 'one_hour',
            'name': '1 Hour Unlimited Energy',
            'description': 'One full hour of unlimited power!',
            'duration_minutes': 60,
            'stars_cost': 8,
            'icon': '⏰',
            'popular': True
        },
        {
            'id': 'twenty_four_hours',
            'name': '24 Hours Unlimited Energy',
            'description': 'Premium: Full day of unlimited energy!',
            'duration_minutes': 1440,
            'stars_cost': 50,
            'icon': '👑',
            'popular': False
        }
    ]
    return jsonify({'packages': packages})


@app.route('/api/stars/purchase', methods=['POST'])
@require_auth
def api_purchase_stars():
    """Purchase a Stars package (simulated - in real app, use Telegram Payments API)."""
    user = request.telegram_user
    data = request.get_json() or {}
    package_id = data.get('package_id')

    packages = {
        'half_hour': {'duration': 30, 'stars': 5},
        'one_hour': {'duration': 60, 'stars': 8},
        'twenty_four_hours': {'duration': 1440, 'stars': 50}
    }

    if package_id not in packages:
        return jsonify({'error': 'Invalid package'}), 400

    pkg = packages[package_id]
    result = activate_unlimited_energy(
        user['telegram_id'],
        pkg['duration'],
        pkg['stars'],
        package_id
    )

    if 'error' in result:
        return jsonify(result), 400

    return jsonify(result)


@app.route('/api/invite/info', methods=['GET'])
@require_auth
def api_invite_info():
    """Get invite/referral info."""
    user = request.telegram_user
    referral_count = get_referral_count(user['telegram_id'])

    return jsonify({
        'referral_code': user['referral_code'],
        'referral_count': referral_count,
        'total_bonus_earned': referral_count * REFERRAL_BONUS,
        'bonus_per_referral': REFERRAL_BONUS
    })


@app.route('/api/invite/apply', methods=['POST'])
@require_auth
def api_apply_referral():
    """Apply a referral code."""
    user = request.telegram_user
    data = request.get_json() or {}
    code = data.get('code', '').strip()

    if not code:
        return jsonify({'error': 'Missing referral code'}), 400

    if user['referred_by']:
        return jsonify({'error': 'Already used a referral code'}), 400

    result = process_referral(code, user['telegram_id'], REFERRAL_BONUS)

    if 'error' in result:
        return jsonify(result), 400

    return jsonify(result)


@app.route('/api/wallet/status', methods=['GET'])
@require_auth
def api_wallet_status():
    """Get wallet connection status."""
    import datetime
    dist_date = datetime.datetime.strptime(DISTRIBUTION_DATE, '%Y-%m-%d')
    now = datetime.datetime.now()
    days_left = (dist_date - now).days

    return jsonify({
        'distribution_date': DISTRIBUTION_DATE,
        'days_left': max(0, days_left),
        'wallet_enabled': days_left <= 7,  # Enable wallet 7 days before distribution
        'balance': request.telegram_user['balance']
    })


@app.route('/api/leaderboard', methods=['GET'])
def api_leaderboard():
    """Get top players."""
    leaders = get_leaderboard(10)
    return jsonify({'leaderboard': leaders})


# ===== Error Handlers =====

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Server error'}), 500


# ===== Database Init (gunicorn icin de calisir) =====
init_db()

# ===== Main =====

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = BOT_TOKEN == 'test_token'
    print(f"\n[FIRE] FINE COIN Server starting on port {port}")
    print(f"[DOG] Mode: {'Development' if debug else 'Production'}")
    print(f"[DATE] Distribution date: {DISTRIBUTION_DATE}\n")
    app.run(host='0.0.0.0', port=port, debug=debug)
