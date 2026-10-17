# syntax=docker/dockerfile:1.7
# ---------------------------------------------------------------------------
# Stage 1: frontend build (Tailwind + esbuild). No Node in the runtime image.
# ---------------------------------------------------------------------------
FROM node:25-alpine AS frontend
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
# INSTALL_DEV=1 (compose.dev) adds the dev group (debug toolbar, pytest); prod images never do.
# No BuildKit cache mount: Railway (temporary host, D-070) rejects mount ids without its
# service-id prefix; the layer is still cached by pyproject.toml + uv.lock.
RUN if [ "$INSTALL_DEV" = "1" ]; then uv sync --frozen --no-install-project; \
    else uv sync --frozen --no-dev --no-install-project; fi \
    && rm -rf /root/.cache/uv

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

# ffmpeg (video transcoding), libmagic (MIME validation), postgres client **16** from PGDG
# (must match the server major for pg_dump/pg_restore — Debian ships 17), gettext
# (compilemessages), curl (healthcheck), restic (backups)
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl gnupg \
    && curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor -o /usr/share/keyrings/pgdg.gpg \
    && . /etc/os-release \
    && echo "deb [signed-by=/usr/share/keyrings/pgdg.gpg] https://apt.postgresql.org/pub/repos/apt ${VERSION_CODENAME}-pgdg main" \
        > /etc/apt/sources.list.d/pgdg.list \
    && apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg libmagic1 postgresql-client-16 gettext restic tini \
    && apt-get purge -y gnupg && apt-get autoremove -y \
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
       python manage.py collectstatic --noinput --ignore=src \
    && chown -R app:app /app/staticfiles

USER app
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=5 CMD /scripts/healthcheck.sh
ENTRYPOINT ["/usr/bin/tini", "--", "/scripts/entrypoint.sh"]
CMD ["web"]
