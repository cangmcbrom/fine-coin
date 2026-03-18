# FINE COIN 🔥🐕 - Telegram Tap-to-Earn Bot

A "This is Fine" meme-themed tap-to-earn Telegram Mini App where users collect FINE Coins by tapping, with a promise of memecoin distribution after 2 months.

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
copy .env.example .env
# Edit .env with your Bot Token from @BotFather
```

### 3. Run the Server
```bash
python run.py
```

The app will be available at `http://localhost:5000`

### 4. Development Mode
Open a browser and go to `http://localhost:5000?user_id=12345678` to test without Telegram.

## 📁 Project Structure
```
fine-coin/
├── server/
│   ├── app.py           # Flask server with all API routes
│   └── database.py      # SQLite database module
├── public/
│   ├── index.html       # Main SPA entry
│   ├── css/style.css    # Complete styling
│   ├── js/
│   │   ├── app.js       # Main app controller
│   │   ├── game.js      # Tap game logic
│   │   ├── upgrades.js  # Upgrades UI
│   │   ├── store.js     # Stars store UI
│   │   ├── invite.js    # Invite/referral UI
│   │   ├── wallet.js    # Wallet UI
│   │   └── api.js       # API client
│   └── assets/          # Images
├── requirements.txt
├── run.py               # Entry point
└── .env.example
```

## 🎮 Features
- **Tap to Earn**: Tap the fire dog to earn FINE coins
- **Energy System**: Energy bar prevents spam (regenerates over time)
- **Upgrades**: Improve tap power, max energy, and recharge rate
- **Stars Store**: Buy unlimited energy with Telegram Stars
- **Referral System**: Invite friends for bonus FINE coins
- **Distribution Countdown**: 2-month countdown to memecoin distribution

## 🔧 Tech Stack
- **Frontend**: Vanilla HTML/CSS/JS + Telegram Mini Apps SDK
- **Backend**: Python Flask
- **Database**: SQLite
- **Auth**: Telegram initData validation

## 🔒 Anti-Cheat
- Server-side rate limiting
- Tap speed validation
- Energy system prevents unlimited farming
- Auto-ban for detected botting
