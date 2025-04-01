# PowerShell Script to run the Telegram bot

# Change to the script's directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# Activate virtual environment if needed
# & \path\to\venv\Scripts\Activate.ps1

# Run the bot
python manage.py run_telegram_bot 