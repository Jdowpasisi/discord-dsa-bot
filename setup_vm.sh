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
# Use manual apt install for better compatibility with Ubuntu 24.04
sudo apt-get install -y \
    libatk1.0-0t64 \
    libatk-bridge2.0-0t64 \
    libcups2t64 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2t64 \
    libatspi2.0-0t64 \
    libnss3 \
    libnspr4 \
    libxkbcommon0 \
    libdrm2 || {
    echo "⚠️  Some packages may have failed. Trying playwright install-deps as fallback..."
    sudo playwright install-deps chromium
}

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Make sure .env file has DISCORD_TOKEN and DATABASE_URL"
echo "  2. Start the bot: python3 main.py"
echo "  3. Or enable systemd service: sudo systemctl start discord-bot"
