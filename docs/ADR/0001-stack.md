# ADR-0001 — Technology stack and version pins

- Status: accepted (2026-09-15)
- Deciders: sole developer (autopilot per AUTOPILOT_PROMPT.md rule 1)

## Context

`docs/ENGINEERING_SPEC.md` §3 pins Python 3.12, Django 5.1, Wagtail 6.x, wagtail-localize,
PostgreSQL 16, Redis 7, Celery, HTMX 2, Alpine 3, Tailwind 3, Docker Compose, nginx, GitHub
Actions, and says "do not swap without a written ADR".

On 2026-09-15:

- Django 5.1 reached end of extended support (Dec 2025). No security releases → `pip-audit`
  in CI (spec §11.3) and spec §8 ("security is not optional") cannot be satisfied.
- Wagtail 6.x is end-of-life; the supported LTS lines are 7.0 (LTS) and later.
- `wagtail-localize` 1.14 (the only maintained line) hard-requires `Django>=5.2` and
  `Wagtail>=7.0`.

## Decision

| Layer | Pinned | Note |
|---|---|---|
| Python | 3.12.x | as spec |
| Django | **5.2 LTS** (`>=5.2,<5.3`) | supported to April 2028; spec said "5.1 LTS-track" — 5.2 *is* the LTS |
| Wagtail | **7.0 LTS** (`>=7.0,<7.1`) | supported to ~Nov 2026 with 7.x upgrades planned in M8 |
| wagtail-localize | 1.14.x | |
| PostgreSQL | 16 (compose) | spec |
| Redis | 7 (compose) | spec |
| Celery | 5.x, static beat schedule | no `django-celery-beat` (DECISIONS D-006) |
| Frontend | Tailwind 3.4, HTMX 2, Alpine 3, bundled with esbuild at image build | no Node at runtime |
| Anti-spam | Cloudflare Turnstile | DECISIONS D-008 |
| PII | in-house `EncryptedTextField` on `cryptography` MultiFernet | DECISIONS D-004 |
| 2FA | django-otp + wagtail-2fa 1.8 | supports Wagtail 7 |
| CSP | django-csp 4.x (nonce) | |

Everything else exactly as spec §3.

## Consequences

- Same major API family as the spec; no code differences for the developer.
- `pip-audit` stays green; security releases keep flowing during the support period (to 31.12.2026).
- The spec text in §3 is superseded by this ADR for the two version numbers only.
