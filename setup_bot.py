"""
FINE COIN - Bot Setup Script
Sets up the bot profile photo and webhook for Telegram Stars payments.
Run this once after deployment.

Usage:
    python setup_bot.py
"""

import os
import sys
import json

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import requests
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN', '')
MINI_APP_URL = os.getenv('MINI_APP_URL', 'https://fine-coin.onrender.com')

if not BOT_TOKEN or BOT_TOKEN == 'test_token':
    print("[ERROR] Please set a valid BOT_TOKEN in .env file!")
    sys.exit(1)

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"


def set_bot_profile_photo():
    """Set the bot's profile photo using the mascot image."""
    photo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'public', 'assets', 'mascot.png')
    
    if not os.path.exists(photo_path):
        print(f"[ERROR] Photo not found: {photo_path}")
        return False
    
    print(f"[INFO] Setting bot profile photo from: {photo_path}")
    
    # Try setMyProfilePhoto (Bot API 9.4+)
    url = f"{TELEGRAM_API}/setMyProfilePhoto"
    
    with open(photo_path, 'rb') as photo_file:
        # InputProfilePhoto with type "static" and photo as file upload
        try:
            # Method 1: Send as multipart with InputProfilePhoto JSON  
            files = {'photo': ('mascot.png', photo_file, 'image/png')}
            data = {
                'photo': json.dumps({'type': 'static'})
            }
            # Actually the photo param is InputProfilePhoto which wraps a file
            # Let's try sending the file directly  
            photo_file.seek(0)
            
            # The API expects: photo as InputProfilePhoto JSON with type and photo file
            import io
            resp = requests.post(url, 
                files={'photo': ('mascot.png', photo_file, 'image/png')},
                timeout=15
            )
            result = resp.json()
            
            if result.get('ok'):
                print("[SUCCESS] Bot profile photo has been set!")
                return True
            else:
                desc = result.get('description', 'Unknown error')
                print(f"[WARNING] setMyProfilePhoto failed: {desc}")
                
                # Fallback: Try the older approach if API version doesn't support it
                print("[INFO] Trying alternative method...")
        except Exception as e:
            print(f"[WARNING] setMyProfilePhoto error: {e}")
    
    # If API method fails, provide manual instructions
    print("[INFO] Automatic profile photo setting is not available.")
    print("[INFO] Please set it manually via @BotFather:")
    print("[INFO]   1. Open @BotFather on Telegram")
    print("[INFO]   2. Send /setuserpic")  
    print("[INFO]   3. Select your bot @fine_coin_earn_bot")
    print("[INFO]   4. Upload: public/assets/mascot.png")
    return False


def set_bot_description():
    """Set the bot's description and short description."""
    # Set description
    url = f"{TELEGRAM_API}/setMyDescription"
    resp = requests.post(url, json={
        'description': '🔥 FINE COIN - Tap to Earn!\n\n'
                       'Tap the "This is Fine" Dog to earn $FINE tokens!\n'
                       '⚡ Upgrade your tap power\n'
                       '⭐ Buy unlimited energy with Stars\n'
                       '🎁 Invite friends for bonuses\n'
                       '💰 Real memecoin distribution coming soon!'
    })
    result = resp.json()
    print(f"[Description] {'Set!' if result.get('ok') else result.get('description', 'Failed')}")

    # Set short description
    url = f"{TELEGRAM_API}/setMyShortDescription"
    resp = requests.post(url, json={
        'short_description': '🔥 Tap to earn $FINE tokens! The "This is Fine" Dog tap-to-earn game.'
    })
    result = resp.json()
    print(f"[Short Desc] {'Set!' if result.get('ok') else result.get('description', 'Failed')}")


def setup_webhook():
    """Setup Telegram webhook for receiving payment events."""
    webhook_url = f"{MINI_APP_URL}/api/telegram/webhook"
    
    print(f"[INFO] Setting webhook to: {webhook_url}")
    
    url = f"{TELEGRAM_API}/setWebhook"
    resp = requests.post(url, json={
        'url': webhook_url,
        'allowed_updates': ['pre_checkout_query', 'message'],
        'drop_pending_updates': True
    })
    result = resp.json()
    
    if result.get('ok'):
        print("[SUCCESS] Webhook has been set!")
        print(f"[INFO] Webhook URL: {webhook_url}")
    else:
        print(f"[ERROR] Webhook setup failed: {result.get('description', 'Unknown error')}")
    
    return result.get('ok', False)


def get_webhook_info():
    """Check current webhook status."""
    url = f"{TELEGRAM_API}/getWebhookInfo"
    resp = requests.get(url)
    result = resp.json()
    
    if result.get('ok'):
        info = result['result']
        print(f"\n[Webhook Info]")
        print(f"  URL: {info.get('url', 'Not set')}")
        print(f"  Pending updates: {info.get('pending_update_count', 0)}")
        print(f"  Last error: {info.get('last_error_message', 'None')}")
        if info.get('last_error_date'):
            print(f"  Last error date: {info.get('last_error_date')}")


def get_bot_info():
    """Get current bot info."""
    url = f"{TELEGRAM_API}/getMe"
    resp = requests.get(url)
    result = resp.json()
    
    if result.get('ok'):
        bot = result['result']
        print(f"\n[Bot Info]")
        print(f"  Name: {bot.get('first_name', '')}")
        print(f"  Username: @{bot.get('username', '')}")
        print(f"  ID: {bot.get('id', '')}")
        print(f"  Can join groups: {bot.get('can_join_groups', False)}")


if __name__ == '__main__':
    print("=" * 50)
    print("🔥 FINE COIN - Bot Setup Script 🐕")
    print("=" * 50)
    
    # Show current bot info
    get_bot_info()
    
    print("\n--- Setting up bot ---\n")
    
    # 1. Set profile photo
    print("[Step 1] Setting bot profile photo...")
    set_bot_profile_photo()
    
    # 2. Set bot description
    print("\n[Step 2] Setting bot description...")
    set_bot_description()
    
    # 3. Setup webhook for payments
    print("\n[Step 3] Setting up webhook for Stars payments...")
    setup_webhook()
    
    # 4. Show webhook info
    get_webhook_info()
    
    print("\n" + "=" * 50)
    print("[DONE] Bot setup complete!")
    print("=" * 50)
    print("\nIf profile photo didn't work via API:")
    print("  1. Open @BotFather on Telegram")
    print("  2. Send /setuserpic")
    print("  3. Select your bot @fine_coin_earn_bot")
    print("  4. Upload the image: public/assets/mascot.png")
    print()
