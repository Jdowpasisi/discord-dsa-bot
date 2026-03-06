#!/bin/bash
# VM Setup Script for Discord DSA Bot
# Run this after deploying to a new VM

set -e  # Exit on error

echo "🚀 Setting up Discord DSA Bot on VM..."

# Check if running in virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Not in virtual environment. Activating venv..."
    source venv/bin/activate
fi

# Install Python dependencies
echo "📦 Installing Python packages..."
pip install -r requirements.txt

# Install Playwright browsers
echo "🌐 Installing Chromium browser for Playwright..."
playwright install chromium

# Install system dependencies for Playwright (requires sudo)
echo "🔧 Installing system dependencies..."
sudo playwright install-deps chromium

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Make sure .env file has DISCORD_TOKEN and DATABASE_URL"
echo "  2. Start the bot: python3 main.py"
echo "  3. Or enable systemd service: sudo systemctl start discord-bot"
