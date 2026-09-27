FROM python:3.11-slim

# libgl1 and libglib2.0-0 are what opencv links against; the slim image omits
# them and `import cv2` fails without them. tesseract is only used by the
# scanned-PDF fallback, but it is small and keeps that path working.
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependencies first, so a code change does not rebuild this layer.
COPY requirements-server.txt .
RUN pip install --no-cache-dir -r requirements-server.txt

COPY . .

# Hosts set $PORT and expect the app to listen on it.
ENV PORT=8080
EXPOSE 8080

# gunicorn rather than Flask's built-in server, which is single-threaded and
# documented as unsuitable for production.
#
# One worker with several threads: the heavy work happens inside PyMuPDF's C
# code, and the job registry lives in this process's memory, so a second
# worker would not see jobs started by the first.
#
# The timeout is generous because a large report can take a minute or two.
CMD exec gunicorn --bind 0.0.0.0:$PORT \
    --workers 1 --threads 8 --timeout 300 \
    --access-logfile - --error-logfile - \
    app:app
