# Shared image for the three FastAPI services.
#
# One image, two services: each container sets SERVICE_NAME (auth-service or
# main-app) and the entrypoint runs that folder.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SERVICE_NAME=auth-service

WORKDIR /app

# Dependencies first, so code edits do not invalidate the pip layer.
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /app/requirements.txt

COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Service code is copied in so the image is self-contained; hosts without a
# bind mount require that.
COPY auth-service /app/auth-service
COPY main-app /app/main-app

RUN useradd --create-home --uid 1000 studystack \
    && chown -R studystack:studystack /app
USER studystack

# An explicit CMD (not just an ENTRYPOINT) so hosts that inspect the image
# find a real command instead of an empty one. The entrypoint still decides
# the folder from SERVICE_NAME and runs this.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

ENTRYPOINT ["/app/entrypoint.sh"]
