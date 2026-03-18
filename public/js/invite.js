/**
 * FINE COIN - Invite Module
 * Handles the referral/invite screen.
 */

const Invite = (() => {
    let referralCode = '';

    function init() {
        // No special init needed
    }

    async function load() {
        try {
            const data = await API.getInviteInfo();
            referralCode = data.referral_code;

            const codeEl = document.getElementById('referral-code');
            const countEl = document.getElementById('invite-count');
            const earnedEl = document.getElementById('invite-earned');

            if (codeEl) codeEl.textContent = data.referral_code;
            if (countEl) countEl.textContent = data.referral_count;
            if (earnedEl) earnedEl.textContent = formatNumber(data.total_bonus_earned);
        } catch (err) {
            console.error('[Invite] Load error:', err);
        }
    }

    function getReferralCode() {
        return referralCode;
    }

    return { init, load, getReferralCode };
})();


// ===== Global invite functions (called from HTML) =====

function copyReferralCode() {
    const code = Invite.getReferralCode();
    if (!code) return;

    if (navigator.clipboard) {
        navigator.clipboard.writeText(code).then(() => {
            showToast('Code copied! 📋', 'success');
        }).catch(() => {
            fallbackCopy(code);
        });
    } else {
        fallbackCopy(code);
    }
}

function fallbackCopy(text) {
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.opacity = '0';
    document.body.appendChild(textarea);
    textarea.select();
    try {
        document.execCommand('copy');
        showToast('Code copied! 📋', 'success');
    } catch {
        showToast('Copy failed, please copy manually', 'error');
    }
    document.body.removeChild(textarea);
}

function shareInviteLink() {
    const code = Invite.getReferralCode();
    if (!code) return;

    const text = `🔥 Join FINE COIN and earn $FINE tokens!\n\nUse my referral code: ${code}\n\nTap to earn before the memecoin distribution! 🐕`;

    if (window.Telegram && window.Telegram.WebApp) {
        // Use Telegram's share functionality
        const botUsername = 'FineCoinBot'; // Replace with actual bot username
        const shareUrl = `https://t.me/${botUsername}?start=${code}`;
        
        window.Telegram.WebApp.openTelegramLink(
            `https://t.me/share/url?url=${encodeURIComponent(shareUrl)}&text=${encodeURIComponent(text)}`
        );
    } else if (navigator.share) {
        navigator.share({ text }).catch(() => {});
    } else {
        copyReferralCode();
        showToast('Invite link copied!', 'success');
    }
}

async function applyReferralCode() {
    const input = document.getElementById('referral-input');
    if (!input) return;

    const code = input.value.trim();
    if (!code) {
        showToast('Please enter a referral code', 'error');
        return;
    }

    try {
        const result = await API.applyReferral(code);
        if (result.success) {
            showToast(`+${result.bonus || 50} FINE bonus! 🎉`, 'success');
            input.value = '';
            
            // Refresh invite data
            Invite.load();

            // Update game balance
            const userData = await API.initUser();
            if (userData.success) {
                Game.updateState(userData.user);
            }
        }
    } catch (err) {
        showToast(err.error || 'Invalid code', 'error');
    }
}
