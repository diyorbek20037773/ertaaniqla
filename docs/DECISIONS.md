# DECISIONS.md — autopilot decisions log

Every choice made without asking (AUTOPILOT rule 1). One line of rationale each. Items marked
**[client]** need the customer's confirmation; the rest are engineering calls.

| # | Date | Decision | Rationale | Reversible? |
|---|---|---|---|---|
| D-001 | 2026-09-15 | Django **5.2 LTS** + Wagtail **7.0 LTS** (spec said 5.1 / 6.x) | 5.1 and 6.x are end-of-life (no security patches; `pip-audit` fails, contradicts spec §8). wagtail-localize 1.14 hard-requires Django ≥ 5.2 and Wagtail ≥ 7.0. Same API family. See ADR-0001. | Yes (pins in pyproject) |
| D-002 | 2026-09-15 | Compose Postgres published on host port **5433** | Developer machine already runs PostgreSQL 18 on 5432. Inside the network it is still `db:5432`. | Yes |
| D-003 | 2026-09-15 | **Wireframe-only UI** until the designer's Figma arrives (developer instruction) | Design is produced separately. All visual decisions confined to `static/src/tokens.css` + `templates/components/` so the design can be applied without touching Python. Milestone **M5b — Design integration** added. `docs/COMPONENT_INVENTORY.md` (ru+uz) is the hand-off to the designer. | n/a |
| D-004 | 2026-09-15 | PII encryption via an in-house `EncryptedTextField` (`apps.core.fields`) on `cryptography.MultiFernet` | 40 lines, fully typed, key rotation with `PII_ENCRYPTION_KEYS` (newest first) — fewer third-party risks than `django-fernet-fields` (unmaintained). | Yes |
| D-005 | 2026-09-15 | Custom `User` model (`apps.users.User`) and custom image/document models (`media_library.PortalImage` / `PortalDocument`) created in M0 | Must exist before the first migration; adding later forces a painful data migration. | Hard later, hence now |
| D-006 | 2026-09-15 | Celery beat uses the static `CELERY_BEAT_SCHEDULE` (no `django-celery-beat`) | Fewer moving parts for a single operator; schedules are code-reviewed. | Yes |
| D-007 | 2026-09-15 | Wagtail admin mounted at `/cms/` (env `CMS_URL_PREFIX`), Django admin at `/django-admin/` | Spec §4.4 / §8: admin URL must not be `/admin/`. | Yes |
| D-008 | 2026-09-15 | Cloudflare **Turnstile** for anti-spam (not hCaptcha) | Spec allows either; Turnstile is free, privacy-friendly, no puzzle for users. Prod refuses to start without a secret key. **[client]** must register the site key. | Yes |
| D-009 | 2026-09-15 | Full-text search config `ertaaniqla` = `simple` + `unaccent` created by a core migration | Spec §7; the same config serves uz (Latin) and ru text. | Yes |
