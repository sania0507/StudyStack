# Root-level Dockerfile.
#
# Why this exists: Render, Railway and Fly all auto-detect a build by looking
# at the repository root. Without a Dockerfile here they scan, find only
# folders, and fail with "could not determine how to build the app".
#
# This file is a thin delegate: the real image definition lives in
# backend/Dockerfile. Because the build context is the repo root, the COPY
# paths below carry the backend/ prefix.
#
# Deploy any of the three services from this file, changing only SERVICE_NAME:
#   SERVICE_NAME=auth-service      (auth API)
#   SERVICE_NAME=main-app          (tasks, subtasks, reminders, sessions)

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SERVICE_NAME=auth-service

WORKDIR /app

COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /app/requirements.txt

COPY backend/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

COPY backend/auth-service /app/auth-service
COPY backend/main-app /app/main-app

RUN useradd --create-home --uid 1000 studystack \
    && chown -R studystack:studystack /app
USER studystack

# An explicit CMD so platform runtime wrappers find a real command. The
# entrypoint chooses the folder from SERVICE_NAME and honours $PORT.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

ENTRYPOINT ["/app/entrypoint.sh"]
