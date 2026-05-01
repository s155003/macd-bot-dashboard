FROM python:3.11-slim

WORKDIR /app

# System deps for pywavelets / numpy / scipy wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot/ ./bot/
COPY dashboard/ ./dashboard/
COPY run_dashboard.py main.py ./

# SQLite DB and any logs live here
VOLUME ["/app/data"]
ENV BOT_DB_PATH=/app/data/bot_state.db

EXPOSE 8000

# Default: launch the dashboard (which can also run the bot in-process)
CMD ["python", "run_dashboard.py"]
