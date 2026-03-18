/**
 * FINE COIN - Stars Store Module
 * Handles the Telegram Stars store UI for unlimited energy packages.
 */

const Store = (() => {
    let storeContainer = null;

    function init() {
        storeContainer = document.getElementById('store-packages');
    }

    async function load() {
        if (!storeContainer) return;

        try {
            const data = await API.getStorePackages();
            renderPackages(data.packages);
        } catch (err) {
            console.error('[Store] Load error:', err);
            storeContainer.innerHTML = '<p style="text-align:center;color:var(--text-muted);padding:40px;">Failed to load packages</p>';
        }
    }

    function renderPackages(packages) {
        if (!storeContainer) return;

        storeContainer.innerHTML = packages.map(pkg => `
            <div class="store-card ${pkg.popular ? 'popular' : ''}" id="store-${pkg.id}">
                ${pkg.popular ? '<div class="popular-badge">🔥 Popular</div>' : ''}
                <div class="store-card-top">
                    <div class="store-icon">${pkg.icon}</div>
                    <div class="store-info">
                        <h3>${pkg.name}</h3>
                        <p>${pkg.description}</p>
                    </div>
                </div>
                <button class="store-buy-btn" onclick="Store.purchase('${pkg.id}', ${pkg.stars_cost})">
                    <span class="star-icon">⭐</span>
                    <span>${pkg.stars_cost} Telegram Stars</span>
                </button>
            </div>
        `).join('');
    }

    async function purchase(packageId, starsCost) {
        // In a real implementation, this would trigger Telegram's payment flow
        // For now, we simulate it
        
        if (window.Telegram && window.Telegram.WebApp) {
            // Attempt to use Telegram's invoice system
            try {
                // Show confirmation
                const confirmed = confirm(
                    `Purchase unlimited energy for ${starsCost} Telegram Stars?`
                );
                
                if (!confirmed) return;

                const result = await API.purchasePackage(packageId);
                
                if (result.success) {
                    showToast('♾️ Unlimited energy activated!', 'success');
                    Game.setUnlimited(true);
                    Game.setEnergy(Game.getEnergy(), Game.getEnergy());
                    
                    // Set timer to disable unlimited when it expires
                    const now = Date.now() / 1000;
                    const remaining = (result.expires_at - now) * 1000;
                    if (remaining > 0) {
                        setTimeout(() => {
                            Game.setUnlimited(false);
                            showToast('Unlimited energy expired ⚡', 'info');
                        }, remaining);
                    }
                }
            } catch (err) {
                showToast(err.error || 'Purchase failed', 'error');
            }
        } else {
            // Development mode simulation
            try {
                const result = await API.purchasePackage(packageId);
                if (result.success) {
                    showToast('♾️ Unlimited energy activated! (Dev mode)', 'success');
                    Game.setUnlimited(true);
                }
            } catch (err) {
                showToast(err.error || 'Purchase failed', 'error');
            }
        }
    }

    return { init, load, purchase };
})();
