# syntax=docker/dockerfile:1.7
# ---------------------------------------------------------------------------
# Stage 1: frontend build (Tailwind + esbuild). No Node in the runtime image.
# ---------------------------------------------------------------------------
FROM node:20-alpine AS frontend
WORKDIR /build
COPY package.json package-lock.json* ./
RUN npm ci --no-audit --no-fund
COPY tailwind.config.js ./
COPY static/src ./static/src
COPY templates ./templates
COPY apps ./apps
RUN npm run build

# ---------------------------------------------------------------------------
# Stage 2: python deps with uv
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS deps
ARG INSTALL_DEV=0
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/opt/venv
COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /uvx /bin/
WORKDIR /app
COPY pyproject.toml uv.lock ./
# INSTALL_DEV=1 (compose.dev) adds the dev group (debug toolbar, pytest); prod images never do
RUN --mount=type=cache,target=/root/.cache/uv \
    if [ "$INSTALL_DEV" = "1" ]; then uv sync --frozen --no-install-project; \
    else uv sync --frozen --no-dev --no-install-project; fi

# ---------------------------------------------------------------------------
# Stage 3: runtime
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime
ARG APP_RELEASE=dev
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=config.settings.prod \
    APP_RELEASE=${APP_RELEASE} \
    MEDIA_ROOT=/srv/media

# ffmpeg (video transcoding), libmagic (MIME validation), postgres client (backups),
# gettext (compilemessages), curl (healthcheck), restic (backups)
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg libmagic1 postgresql-client gettext curl restic tini \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1000 app && useradd --uid 1000 --gid app --create-home app \
    && mkdir -p /srv/media /app/staticfiles /backups && chown -R app:app /srv/media /app /backups

WORKDIR /app
COPY --from=deps /opt/venv /opt/venv
COPY --chown=app:app . .
COPY --from=frontend --chown=app:app /build/static/dist ./static/dist
COPY --chown=app:app docker/scripts /scripts
RUN chmod +x /scripts/*.sh \
    && DJANGO_SECRET_KEY=build-only PII_ENCRYPTION_KEYS=build-only TURNSTILE_SECRET_KEY=build-only \
       DJANGO_SETTINGS_MODULE=config.settings.build \
       python manage.py compilemessages --ignore=node_modules \
    && DJANGO_SECRET_KEY=build-only PII_ENCRYPTION_KEYS=build-only TURNSTILE_SECRET_KEY=build-only \
       DJANGO_SETTINGS_MODULE=config.settings.build \
       python manage.py collectstatic --noinput \
    && chown -R app:app /app/staticfiles

USER app
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=5 CMD /scripts/healthcheck.sh
ENTRYPOINT ["/usr/bin/tini", "--", "/scripts/entrypoint.sh"]
CMD ["web"]
