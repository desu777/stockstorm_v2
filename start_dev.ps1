#!/usr/bin/env pwsh
# Script to start all required services for development environment

Write-Host "Starting StockStorm Development Environment" -ForegroundColor Green

# Start Redis for WebSocket and caching
Write-Host "Starting Redis Server..." -ForegroundColor Cyan
Start-Process -NoNewWindow -FilePath "redis-server"

# Start Django development server
Write-Host "Starting Django Server..." -ForegroundColor Cyan
cd v1
python manage.py runserver

# To kill all processes when needed:
# Get-Process -Name python, redis-server | Stop-Process
