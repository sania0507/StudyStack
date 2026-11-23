# Shared image for all three FastAPI services.
# Docker Compose builds this once and each service points at it with a
# different WORKDIR and CMD.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencies first, so code edits do not invalidate the pip layer.
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /app/requirements.txt

COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Runs as a non-root user, which is what most hosts expect.
RUN useradd --create-home --uid 1000 studystack \
    && chown -R studystack:studystack /app
USER studystack

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
