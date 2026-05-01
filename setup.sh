#!/usr/bin/env bash
# setup.sh — one-shot project setup
# Usage:  bash setup.sh

set -e

echo "🔧 Setting up macd-bot..."
echo

# 1. Create a virtual environment
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
fi

# 2. Activate and install
echo "📥 Installing dependencies..."
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

# 3. Create .env from template if missing
if [ ! -f ".env" ]; then
    echo "📝 Creating .env from template..."
    cp .env.example .env
    echo "   ⚠️  Edit .env and add your Alpaca API keys before running the bot."
fi

# 4. Make sure data dir exists for SQLite
mkdir -p data

# 5. Run tests to verify install
echo
echo "🧪 Running tests..."
python tests/test_strategy.py
python tests/test_store.py
python tests/test_server.py

echo
echo "✅ Setup complete!"
echo
echo "Next steps:"
echo "  1. Edit .env and add ALPACA_API_KEY and ALPACA_SECRET_KEY"
echo "     (paper trading keys: https://app.alpaca.markets/paper/dashboard/overview)"
echo "  2. Activate the virtual environment:  source .venv/bin/activate"
echo "  3. Launch the dashboard:              python run_dashboard.py"
echo "  4. Open in browser:                   http://localhost:8000"
