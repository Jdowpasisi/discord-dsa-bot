#!/bin/bash
# Post-update script - Run this after git pull

set -e

echo "🔄 Updating bot dependencies..."

# Activate virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    source venv/bin/activate
fi

# Update Python packages
pip install -r requirements.txt --upgrade

# Ensure Playwright browser is installed (idempotent)
playwright install chromium

echo "✅ Update complete!"
echo ""
echo "To apply changes:"
echo "  sudo systemctl daemon-reload  # If service file changed"
echo "  sudo systemctl restart discord-bot  # or 'discordbot' if that's your service name"
