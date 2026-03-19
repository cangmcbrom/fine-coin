/**
 * FINE COIN - Stars Store Module
 * Handles the Telegram Stars store UI and real payment flow.
 * Uses Telegram's createInvoiceLink + openInvoice for real Stars payments.
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
                <button class="store-buy-btn" id="buy-${pkg.id}" onclick="Store.purchase('${pkg.id}', ${pkg.stars_cost})">
                    <span class="star-icon">⭐</span>
                    <span>${pkg.stars_cost} Telegram Stars</span>
                </button>
            </div>
        `).join('');
    }

    function setButtonLoading(packageId, loading) {
        const btn = document.getElementById(`buy-${packageId}`);
        if (!btn) return;
        
        if (loading) {
            btn.disabled = true;
            btn.innerHTML = '<span class="star-icon">⏳</span><span>Processing...</span>';
            btn.classList.add('loading');
        } else {
            btn.disabled = false;
            btn.classList.remove('loading');
            // Will be restored on next load()
        }
    }

    async function purchase(packageId, starsCost) {
        const tg = window.Telegram && window.Telegram.WebApp;

        if (tg && tg.initData) {
            // ===== PRODUCTION: Real Telegram Stars Payment =====
            await purchaseWithTelegramStars(packageId, starsCost);
        } else {
            // ===== DEV MODE: Simulated payment =====
            await purchaseDevMode(packageId, starsCost);
        }
    }

    async function purchaseWithTelegramStars(packageId, starsCost) {
        const tg = window.Telegram.WebApp;

        setButtonLoading(packageId, true);

        try {
            // Step 1: Get invoice link from our backend
            const invoiceData = await API.createInvoice(packageId);

            if (!invoiceData.success || !invoiceData.invoice_url) {
                showToast(invoiceData.error || 'Failed to create payment', 'error');
                setButtonLoading(packageId, false);
                return;
            }

            const invoiceUrl = invoiceData.invoice_url;

            // Step 2: Open Telegram's native payment dialog
            tg.openInvoice(invoiceUrl, async (status) => {
                console.log('[Store] Invoice status:', status);

                if (status === 'paid') {
                    // Payment successful!
                    showToast('⭐ Payment received! Activating...', 'success');

                    // Step 3: Verify payment was processed on backend
                    // Small delay to allow webhook to process
                    await waitForPaymentProcessing(packageId);

                } else if (status === 'cancelled') {
                    showToast('Payment cancelled', 'info');
                    setButtonLoading(packageId, false);
                    load(); // Refresh packages
                } else if (status === 'failed') {
                    showToast('Payment failed. Please try again.', 'error');
                    setButtonLoading(packageId, false);
                    load();
                } else if (status === 'pending') {
                    showToast('Payment is being processed...', 'info');
                    // Will be handled by webhook
                    await waitForPaymentProcessing(packageId);
                } else {
                    // Unknown status
                    setButtonLoading(packageId, false);
                    load();
                }
            });

        } catch (err) {
            console.error('[Store] Purchase error:', err);
            showToast(err.error || 'Payment error. Please try again.', 'error');
            setButtonLoading(packageId, false);
            load();
        }
    }

    async function waitForPaymentProcessing(packageId) {
        // Poll the backend to check if the payment was processed
        // The webhook may take a moment to fire
        let attempts = 0;
        const maxAttempts = 10;
        const delayMs = 1500;

        const checkPayment = async () => {
            attempts++;
            try {
                const result = await API.checkPayment();

                if (result.has_unlimited) {
                    // Payment processed! Activate unlimited energy
                    showToast('♾️ Unlimited energy activated!', 'success');
                    Game.setUnlimited(true);
                    Game.setEnergy(result.current_energy, result.max_energy);

                    // Set timer to disable unlimited when it expires
                    if (result.unlimited_until) {
                        const now = Date.now() / 1000;
                        const remaining = (result.unlimited_until - now) * 1000;
                        if (remaining > 0) {
                            setTimeout(() => {
                                Game.setUnlimited(false);
                                showToast('Unlimited energy expired ⚡', 'info');
                            }, remaining);
                        }
                    }

                    setButtonLoading(packageId, false);
                    load();
                    return;
                }

                if (attempts < maxAttempts) {
                    // Keep polling
                    setTimeout(checkPayment, delayMs);
                } else {
                    // Timeout - payment might still process via webhook
                    showToast('Payment is being verified. It will activate shortly!', 'info');
                    setButtonLoading(packageId, false);
                    load();
                }
            } catch (err) {
                console.error('[Store] Check payment error:', err);
                if (attempts < maxAttempts) {
                    setTimeout(checkPayment, delayMs);
                } else {
                    showToast('Verification timeout. If paid, it will activate soon.', 'info');
                    setButtonLoading(packageId, false);
                    load();
                }
            }
        };

        // Start checking after a short delay
        setTimeout(checkPayment, 1000);
    }

    async function purchaseDevMode(packageId, starsCost) {
        // Development mode - simulate payment with confirmation
        const confirmed = confirm(
            `[DEV MODE] Purchase unlimited energy for ${starsCost} Telegram Stars?\n\nIn production, this will open Telegram's real payment dialog.`
        );

        if (!confirmed) return;

        try {
            const result = await API.purchasePackage(packageId);
            if (result.success) {
                showToast('♾️ Unlimited energy activated! (Dev mode)', 'success');
                Game.setUnlimited(true);
                Game.setEnergy(Game.getEnergy(), Game.getEnergy());

                // Set timer for expiration
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
    }

    return { init, load, purchase };
})();
