/**
 * FINE COIN - Main App Controller
 * Initializes all modules, handles tab switching, and manages the app lifecycle.
 */

(async function() {
    'use strict';

    // ===== Telegram WebApp Setup =====
    let tg = null;
    if (window.Telegram && window.Telegram.WebApp) {
        tg = window.Telegram.WebApp;
        tg.ready();
        tg.expand();
        
        // Theme
        document.documentElement.style.setProperty('--tg-theme-bg-color', tg.backgroundColor || '#0d0d0f');
        
        // Header color
        try {
            tg.setHeaderColor('#0d0d0f');
        } catch(e) {}

        // Disable closing by swipe
        try {
            tg.disableClosingConfirmation && tg.disableClosingConfirmation();
        } catch(e) {}
    }

    // ===== Loading Screen =====
    const loadingScreen = document.getElementById('loading-screen');
    const mainApp = document.getElementById('main-app');

    async function startApp() {
        try {
            // Init modules
            Upgrades.init();
            Store.init();
            Invite.init();
            Wallet.init();

            // Fetch user data
            const data = await API.initUser();
            
            if (data.success) {
                Game.init(data.user);
                updateCountdown(data.user.distribution_date);
            } else {
                throw new Error('Failed to init user');
            }

            // Hide loading, show app
            setTimeout(() => {
                loadingScreen.classList.add('fade-out');
                mainApp.classList.remove('hidden');
                
                setTimeout(() => {
                    loadingScreen.style.display = 'none';
                }, 500);
            }, 1500); // Min loading time for polish

        } catch (err) {
            console.error('[App] Init error:', err);
            // Still show the app, just with default values
            Game.init({
                balance: 0,
                current_energy: 1000,
                max_energy: 1000,
                tap_power: 0.2,
                recharge_rate: 10,
                has_unlimited_energy: false,
                total_taps: 0,
                distribution_date: '2026-05-19'
            });
            
            updateCountdown('2026-05-19');

            setTimeout(() => {
                loadingScreen.classList.add('fade-out');
                mainApp.classList.remove('hidden');
            }, 1500);
        }
    }

    // ===== Tab Switching =====
    window.switchTab = function(tabName) {
        // Update nav buttons
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tabName);
        });

        // Update screens
        document.querySelectorAll('.screen').forEach(screen => {
            screen.classList.toggle('active', screen.dataset.screen === tabName);
        });

        // Load screen data
        switch(tabName) {
            case 'upgrades':
                Upgrades.load();
                break;
            case 'store':
                Store.load();
                break;
            case 'invite':
                Invite.load();
                break;
            case 'wallet':
                Wallet.load();
                break;
            case 'play':
                // Refresh energy
                API.getEnergy().then(data => {
                    Game.setEnergy(data.current_energy, data.max_energy);
                    Game.setUnlimited(data.has_unlimited);
                }).catch(() => {});
                break;
        }
    };

    // ===== Countdown =====
    function updateCountdown(distributionDate) {
        const countdownEl = document.getElementById('countdown-days');
        if (!countdownEl || !distributionDate) return;

        function tick() {
            const now = new Date();
            const dist = new Date(distributionDate);
            const diff = dist - now;

            if (diff <= 0) {
                countdownEl.textContent = 'Distribution Active!';
                return;
            }

            const days = Math.floor(diff / (1000 * 60 * 60 * 24));
            const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));

            countdownEl.textContent = `${days}d ${hours}h`;
        }

        tick();
        setInterval(tick, 60000); // Update every minute
    }

    // ===== Start =====
    startApp();
})();
