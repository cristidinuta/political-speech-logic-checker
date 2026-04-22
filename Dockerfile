FROM python:3.11-slim

# Install SWI-Prolog
RUN apt-get update && \
    apt-get install -y --no-install-recommends swi-prolog && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY fallacies.pl .

CMD gunicorn app:app --bind 0.0.0.0:${PORT:-5000} --workers 2 --timeout 60
