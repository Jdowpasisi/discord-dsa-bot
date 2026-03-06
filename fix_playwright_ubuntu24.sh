#!/bin/bash
# Quick fix for Playwright dependencies on Ubuntu 24.04

echo "🔧 Installing Playwright system dependencies for Ubuntu 24.04..."

sudo apt-get update
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
    libdrm2

echo ""
echo "✅ Dependencies installed!"
echo ""
echo "Now run:"
echo "  source venv/bin/activate"
echo "  playwright install chromium"
echo "  sudo systemctl daemon-reload"
echo "  sudo systemctl restart discordbot"
