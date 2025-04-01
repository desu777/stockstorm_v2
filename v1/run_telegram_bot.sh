#!/bin/bash
# Script to run the Telegram bot

# Activate virtual environment if needed
# source /path/to/venv/bin/activate

# Run the bot
cd "$(dirname "$0")"
python manage.py run_telegram_bot 