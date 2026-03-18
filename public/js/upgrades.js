/**
 * FINE COIN - Upgrades Module
 * Handles the upgrades screen UI and purchase logic.
 */

const Upgrades = (() => {
    let upgradesList = null;

    function init() {
        upgradesList = document.getElementById('upgrades-list');
    }

    async function load() {
        if (!upgradesList) return;

        try {
            const data = await API.getUpgrades();
            renderUpgrades(data.upgrades, data.balance);
        } catch (err) {
            console.error('[Upgrades] Load error:', err);
            upgradesList.innerHTML = '<p style="text-align:center;color:var(--text-muted);padding:40px;">Failed to load upgrades</p>';
        }
    }

    function renderUpgrades(upgrades, balance) {
        if (!upgradesList) return;

        // Update balance display
        const balanceEl = document.getElementById('upgrades-balance');
        if (balanceEl) balanceEl.textContent = formatNumber(balance);

        upgradesList.innerHTML = upgrades.map(upgrade => {
            const isMaxed = upgrade.current_level >= upgrade.max_level;
            const canAfford = upgrade.can_afford;

            let btnClass = isMaxed ? 'max-level' : (canAfford ? 'can-afford' : 'cant-afford');
            let btnText = isMaxed ? '✅ MAX' : `${formatNumber(upgrade.cost)} FINE`;

            let valueDisplay = '';
            if (!isMaxed && upgrade.next_value !== null) {
                valueDisplay = `<span class="current-val">${upgrade.current_value}</span> → <span class="next-val">${upgrade.next_value}</span>`;
            } else {
                valueDisplay = `<span class="current-val">${upgrade.current_value}</span>`;
            }

            return `
                <div class="upgrade-card" id="upgrade-${upgrade.type}">
                    <div class="upgrade-top">
                        <div class="upgrade-icon">${upgrade.icon}</div>
                        <div class="upgrade-info">
                            <div class="upgrade-name">${upgrade.name}</div>
                            <div class="upgrade-desc">${upgrade.description}</div>
                        </div>
                        <div class="upgrade-level-badge">Lv.${upgrade.current_level}</div>
                    </div>
                    <div class="upgrade-bottom">
                        <div class="upgrade-values">${valueDisplay}</div>
                        <button class="upgrade-buy-btn ${btnClass}" 
                                ${isMaxed || !canAfford ? '' : `onclick="Upgrades.buy('${upgrade.type}')"`}
                                ${isMaxed ? 'disabled' : ''}>
                            ${btnText}
                        </button>
                    </div>
                </div>
            `;
        }).join('');
    }

    async function buy(type) {
        try {
            const result = await API.buyUpgrade(type);

            if (result.success) {
                showToast(`Upgraded to Lv.${result.new_level}! 🎉`, 'success');

                // Update game state
                if (type === 'tap_power') {
                    Game.setTapPower(result.new_level * 0.2);
                } else if (type === 'max_energy') {
                    const newMax = 1000 + (result.new_level - 1) * 500;
                    Game.setEnergy(newMax, newMax);
                } else if (type === 'recharge_rate') {
                    Game.setRechargeRate(10 + (result.new_level - 1) * 5);
                }

                Game.setBalance(result.new_balance);

                // Reload upgrades
                load();
            }
        } catch (err) {
            if (err.error === 'Insufficient balance') {
                showToast('Not enough FINE coins! 💰', 'error');
            } else if (err.error === 'Max level reached') {
                showToast('Already at max level! ✅', 'info');
            } else {
                showToast(err.error || 'Purchase failed', 'error');
            }
        }
    }

    return { init, load, buy };
})();
