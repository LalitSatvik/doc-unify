FROM python:3.11-slim

WORKDIR /app

# tesseract-ocr is a system binary pytesseract shells out to (OCR fallback
# for scanned PDFs and image ingestion) — not installable via pip.
RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --no-cache-dir -e ".[dev]"

COPY app ./app
COPY tests ./tests
COPY alembic.ini ./alembic.ini
COPY migrations ./migrations
COPY start.sh ./start.sh
RUN chmod +x ./start.sh

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
