FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8788

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        git \
        libjpeg62-turbo \
        zlib1g \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

COPY . .

RUN mkdir -p /app/var/data /app/logs \
    && adduser --system --group --home /app matchdrawer \
    && chown -R matchdrawer:matchdrawer /app

USER matchdrawer

EXPOSE 8788

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import os, urllib.request; port=os.getenv('PORT','8788'); urllib.request.urlopen(f'http://127.0.0.1:{port}/login?sso=0', timeout=3)"

CMD ["sh", "-c", "gunicorn -c gunicorn.conf.py --bind 0.0.0.0:${PORT:-8788} app:app"]
