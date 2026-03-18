/**
 * FINE COIN - Wallet Module
 * Handles the wallet screen with countdown to distribution.
 */

const Wallet = (() => {
    function init() {
        // No special init needed
    }

    async function load() {
        try {
            const data = await API.getWalletStatus();

            const daysEl = document.getElementById('wallet-days-left');
            const balanceEl = document.getElementById('wallet-balance');

            if (daysEl) daysEl.textContent = data.days_left;
            if (balanceEl) balanceEl.textContent = formatNumber(data.balance);

            // If wallet is enabled (7 days before distribution)
            if (data.wallet_enabled) {
                const iconEl = document.querySelector('.wallet-icon-large');
                if (iconEl) iconEl.textContent = '🔓';
                
                const titleEl = document.querySelector('.wallet-card-title');
                if (titleEl) titleEl.textContent = 'Connect Your Wallet';
                
                const descEl = document.querySelector('.wallet-card-desc');
                if (descEl) {
                    descEl.innerHTML = `
                        Wallet connection is now available! Connect your wallet 
                        to receive your <strong>$FINE</strong> memecoin distribution.
                    `;
                }
            }
        } catch (err) {
            console.error('[Wallet] Load error:', err);
        }
    }

    return { init, load };
})();
