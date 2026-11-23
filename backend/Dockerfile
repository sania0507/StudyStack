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

# The service code lives in sibling folders (auth-service, main-app,
# analytics-service). Copying them all makes the image self-contained, which
# is required on hosts like Render where there is no bind mount. Each service
# then runs from its own folder via working_dir / dockerWorkDir.
COPY auth-service /app/auth-service
COPY main-app /app/main-app
COPY analytics-service /app/analytics-service

# Runs as a non-root user, which is what most hosts expect.
RUN useradd --create-home --uid 1000 studystack \
    && chown -R studystack:studystack /app
USER studystack

# The entrypoint reads SERVICE_NAME to choose its folder, so the image has a
# sensible default even when Render runs the CMD instead of dockerCommand.
ENV SERVICE_NAME=auth-service

ENTRYPOINT ["/app/entrypoint.sh"]
