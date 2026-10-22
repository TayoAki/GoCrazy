# The research app for a server such as Railway: Python, ffmpeg for frames and scene cuts, and the app.
# Data (SQLite database and media) goes to DATA_DIR, or the Railway volume's mount path when one is attached.
FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY research_app ./research_app

ENV HOST=0.0.0.0 \
    PORT=8000 \
    PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["python", "-m", "research_app"]
