"""
FINE COIN - Run Script
Starts the Flask server.
"""

import os
import sys

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Add the project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from server.app import app
from server.database import init_db

if __name__ == '__main__':
    # Initialize database
    init_db()
    
    # Get config
    port = int(os.getenv('PORT', 5000))
    bot_token = os.getenv('BOT_TOKEN', 'test_token')
    debug = bot_token == 'test_token'
    
    print("=" * 50)
    print("[FIRE] FINE COIN - Tap to Earn Bot [DOG]")
    print("=" * 50)
    print(f"[WEB] Server: http://localhost:{port}")
    print(f"[MODE] {'Development' if debug else 'Production'}")
    print(f"[DIR] Static: {os.path.abspath('public')}")
    print("=" * 50)
    print()
    print("Open http://localhost:5000?user_id=12345678 to test")
    print()
    
    app.run(host='0.0.0.0', port=port, debug=debug)
