/**
 * FINE COIN - API Client
 * Handles all communication with the backend server.
 */

const API = (() => {
    const BASE_URL = window.location.origin;
    let telegramInitData = '';
    let devTelegramId = null;

    function init() {
        // Try to get Telegram WebApp initData
        if (window.Telegram && window.Telegram.WebApp) {
            telegramInitData = window.Telegram.WebApp.initData || '';
        }

        // Development fallback
        if (!telegramInitData) {
            const params = new URLSearchParams(window.location.search);
            devTelegramId = params.get('user_id') || '12345678';
            console.log('[API] Dev mode, user_id:', devTelegramId);
        }
    }

    async function request(endpoint, method = 'GET', body = null) {
        const headers = {
            'Content-Type': 'application/json',
        };

        if (telegramInitData) {
            headers['X-Telegram-Init-Data'] = telegramInitData;
        }

        let url = `${BASE_URL}${endpoint}`;

        // Dev mode: append telegram_id
        if (!telegramInitData && devTelegramId) {
            const separator = url.includes('?') ? '&' : '?';
            url += `${separator}telegram_id=${devTelegramId}`;
        }

        const options = {
            method,
            headers,
        };

        if (body && (method === 'POST' || method === 'PUT')) {
            if (!telegramInitData && devTelegramId) {
                body.telegram_id = parseInt(devTelegramId);
            }
            options.body = JSON.stringify(body);
        }

        try {
            const response = await fetch(url, options);
            const data = await response.json();

            if (!response.ok) {
                throw { status: response.status, ...data };
            }

            return data;
        } catch (error) {
            if (error.status) throw error;
            console.error('[API] Network error:', error);
            throw { error: 'Network error', status: 0 };
        }
    }

    // ===== User =====
    function initUser() {
        return request('/api/user/init', 'POST', {});
    }

    // ===== Game =====
    function tap(taps = 1) {
        return request('/api/game/tap', 'POST', { taps });
    }

    function getEnergy() {
        return request('/api/game/energy', 'GET');
    }

    // ===== Upgrades =====
    function getUpgrades() {
        return request('/api/upgrades/list', 'GET');
    }

    function buyUpgrade(type) {
        return request('/api/upgrades/buy', 'POST', { type });
    }

    // ===== Stars Store =====
    function getStorePackages() {
        return request('/api/stars/packages', 'GET');
    }

    function purchasePackage(packageId) {
        return request('/api/stars/purchase', 'POST', { package_id: packageId });
    }

    // ===== Invite =====
    function getInviteInfo() {
        return request('/api/invite/info', 'GET');
    }

    function applyReferral(code) {
        return request('/api/invite/apply', 'POST', { code });
    }

    // ===== Wallet =====
    function getWalletStatus() {
        return request('/api/wallet/status', 'GET');
    }

    // ===== Leaderboard =====
    function getLeaderboard() {
        return request('/api/leaderboard', 'GET');
    }

    // Initialize on load
    init();

    return {
        initUser,
        tap,
        getEnergy,
        getUpgrades,
        buyUpgrade,
        getStorePackages,
        purchasePackage,
        getInviteInfo,
        applyReferral,
        getWalletStatus,
        getLeaderboard,
    };
})();
