/**
 * FINE COIN - Game (Tap) Module
 * Handles the main tap gameplay, energy bar, and visual effects.
 */

const Game = (() => {
    // State
    let balance = 0;
    let currentEnergy = 1000;
    let maxEnergy = 1000;
    let tapPower = 0.2;
    let rechargeRate = 10; // per minute
    let hasUnlimited = false;
    let totalTaps = 0;

    // DOM
    let balanceEl, energyBarFill, energyText, energyIcon;
    let tapButton, tapEffects, fireRing;
    let statTapPower, statTotalTaps;
    let unlimitedBadge;

    // Tap batching
    let pendingTaps = 0;
    let tapBatchTimer = null;
    const TAP_BATCH_DELAY = 300; // ms

    // Energy regen timer
    let energyRegenInterval = null;

    function init(userData) {
        // Cache DOM elements
        balanceEl = document.getElementById('balance-amount');
        energyBarFill = document.getElementById('energy-bar-fill');
        energyText = document.getElementById('energy-text');
        energyIcon = document.getElementById('energy-icon');
        tapButton = document.getElementById('tap-button');
        tapEffects = document.getElementById('tap-effects');
        fireRing = document.getElementById('fire-ring');
        statTapPower = document.getElementById('stat-tap-power');
        statTotalTaps = document.getElementById('stat-total-taps');
        unlimitedBadge = document.getElementById('unlimited-badge');

        // Set initial state from server
        updateState(userData);

        // Set up tap handler
        setupTapHandler();

        // Start energy regeneration
        startEnergyRegen();
    }

    function updateState(data) {
        balance = data.balance || 0;
        currentEnergy = data.current_energy || 0;
        maxEnergy = data.max_energy || 1000;
        tapPower = data.tap_power || 0.2;
        rechargeRate = data.recharge_rate || 10;
        hasUnlimited = data.has_unlimited_energy || false;
        totalTaps = data.total_taps || 0;

        updateUI();
    }

    function updateUI() {
        // Balance
        if (balanceEl) {
            balanceEl.textContent = formatNumber(balance);
        }

        // Energy bar
        const energyPercent = maxEnergy > 0 ? (currentEnergy / maxEnergy) * 100 : 0;
        if (energyBarFill) {
            energyBarFill.style.width = `${Math.min(100, energyPercent)}%`;
        }
        if (energyText) {
            energyText.textContent = `${Math.floor(currentEnergy)} / ${maxEnergy}`;
        }

        // Unlimited badge
        if (unlimitedBadge) {
            if (hasUnlimited) {
                unlimitedBadge.classList.remove('hidden');
                energyIcon.textContent = '♾️';
            } else {
                unlimitedBadge.classList.add('hidden');
                energyIcon.textContent = '⚡';
            }
        }

        // Stats
        if (statTapPower) statTapPower.textContent = tapPower;
        if (statTotalTaps) statTotalTaps.textContent = formatCompact(totalTaps);
    }

    function setupTapHandler() {
        if (!tapButton) return;

        // Prevent context menu
        tapButton.addEventListener('contextmenu', (e) => e.preventDefault());

        // Multi-touch support
        tapButton.addEventListener('touchstart', (e) => {
            e.preventDefault();
            for (let i = 0; i < e.changedTouches.length; i++) {
                const touch = e.changedTouches[i];
                handleTap(touch.clientX, touch.clientY);
            }
        }, { passive: false });

        // Mouse click fallback
        tapButton.addEventListener('mousedown', (e) => {
            e.preventDefault();
            handleTap(e.clientX, e.clientY);
        });
    }

    function handleTap(x, y) {
        // Check energy
        if (!hasUnlimited && currentEnergy < 1) {
            showToast('No energy! Wait for recharge ⚡', 'error');
            return;
        }

        // Haptic feedback
        if (window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.HapticFeedback) {
            window.Telegram.WebApp.HapticFeedback.impactOccurred('light');
        }

        // Visual effects
        createTapEffect(x, y);
        animateTapButton();

        // Optimistic update
        balance = Math.round((balance + tapPower) * 100) / 100;
        if (!hasUnlimited) {
            currentEnergy = Math.max(0, currentEnergy - 1);
        }
        totalTaps++;

        updateUI();

        // Batch taps for server
        pendingTaps++;
        if (tapBatchTimer) clearTimeout(tapBatchTimer);
        tapBatchTimer = setTimeout(flushTaps, TAP_BATCH_DELAY);
    }

    async function flushTaps() {
        if (pendingTaps <= 0) return;
        const taps = pendingTaps;
        pendingTaps = 0;

        try {
            const result = await API.tap(taps);
            if (result.success) {
                // Sync with server values
                balance = result.new_balance;
                currentEnergy = result.current_energy;
                maxEnergy = result.max_energy;
                hasUnlimited = result.has_unlimited;
                updateUI();
            }
        } catch (err) {
            console.error('[Game] Tap error:', err);
            if (err.error === 'No energy') {
                currentEnergy = 0;
                updateUI();
            }
        }
    }

    function createTapEffect(x, y) {
        if (!tapEffects) return;

        const el = document.createElement('div');
        el.className = 'tap-text';
        el.textContent = `+${tapPower}`;

        // Position relative to tap effects container
        const rect = tapEffects.getBoundingClientRect();
        const offsetX = x - rect.left - 30 + (Math.random() * 40 - 20);
        const offsetY = y - rect.top - 20;

        el.style.left = `${offsetX}px`;
        el.style.top = `${offsetY}px`;

        tapEffects.appendChild(el);

        setTimeout(() => el.remove(), 800);
    }

    function animateTapButton() {
        if (!tapButton) return;
        tapButton.classList.remove('tapped');
        void tapButton.offsetWidth; // Force reflow
        tapButton.classList.add('tapped');
    }

    function startEnergyRegen() {
        if (energyRegenInterval) clearInterval(energyRegenInterval);

        energyRegenInterval = setInterval(() => {
            if (hasUnlimited) return;
            if (currentEnergy >= maxEnergy) return;

            // Regen per second = rechargeRate / 60
            const regenPerSecond = rechargeRate / 60;
            currentEnergy = Math.min(maxEnergy, currentEnergy + regenPerSecond);
            updateUI();
        }, 1000);
    }

    function setBalance(val) {
        balance = val;
        updateUI();
    }

    function setEnergy(current, max) {
        currentEnergy = current;
        if (max) maxEnergy = max;
        updateUI();
    }

    function setTapPower(val) {
        tapPower = val;
        updateUI();
    }

    function setRechargeRate(val) {
        rechargeRate = val;
    }

    function setUnlimited(val) {
        hasUnlimited = val;
        updateUI();
    }

    function getBalance() { return balance; }
    function getEnergy() { return currentEnergy; }

    return {
        init,
        updateState,
        setBalance,
        setEnergy,
        setTapPower,
        setRechargeRate,
        setUnlimited,
        getBalance,
        getEnergy,
        updateUI,
    };
})();


// ===== Utility Functions (global) =====

function formatNumber(num) {
    if (typeof num !== 'number') num = parseFloat(num) || 0;
    if (num >= 1000000) return (num / 1000000).toFixed(2) + 'M';
    if (num >= 10000) return (num / 1000).toFixed(1) + 'K';
    if (num >= 1000) return num.toFixed(1);
    return num % 1 === 0 ? num.toString() : num.toFixed(1);
}

function formatCompact(num) {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return num.toString();
}

function showToast(message, type = 'info', duration = 2000) {
    const toast = document.getElementById('toast');
    if (!toast) return;

    toast.textContent = message;
    toast.className = `toast ${type}`;

    setTimeout(() => {
        toast.classList.add('fade-out');
        setTimeout(() => {
            toast.className = 'toast hidden';
        }, 300);
    }, duration);
}
