FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# The bot stores SQLite data here.
RUN mkdir -p /app/data

# Long-polling by default; set WEBHOOK_URL to switch to webhook mode.
CMD ["python", "-m", "bot.main"]
