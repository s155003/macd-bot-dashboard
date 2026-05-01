# setup.ps1 — one-shot project setup for Windows
# Usage (in PowerShell):  .\setup.ps1

$ErrorActionPreference = "Stop"

Write-Host "Setting up macd-bot..." -ForegroundColor Cyan

# 1. Create venv
if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment..."
    python -m venv .venv
}

# 2. Activate and install
Write-Host "Installing dependencies..."
& .\.venv\Scripts\Activate.ps1
python -m pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

# 3. Create .env from template
if (-not (Test-Path ".env")) {
    Write-Host "Creating .env from template..."
    Copy-Item .env.example .env
    Write-Host "   Edit .env and add your Alpaca API keys before running." -ForegroundColor Yellow
}

# 4. Data dir for SQLite
if (-not (Test-Path "data")) {
    New-Item -ItemType Directory -Path "data" | Out-Null
}

# 5. Run tests
Write-Host ""
Write-Host "Running tests..."
python tests\test_strategy.py
python tests\test_store.py
python tests\test_server.py

Write-Host ""
Write-Host "Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Edit .env and add ALPACA_API_KEY and ALPACA_SECRET_KEY"
Write-Host "     (paper trading keys: https://app.alpaca.markets/paper/dashboard/overview)"
Write-Host "  2. Activate venv:        .\.venv\Scripts\Activate.ps1"
Write-Host "  3. Launch dashboard:     python run_dashboard.py"
Write-Host "  4. Open in browser:      http://localhost:8000"
