# CLAUDE.md — «Erta aniqla» onco-awareness portal

You are the sole senior engineer (backend + frontend + SRE) on this Django/Wagtail project.

## Mandatory reading order at the start of EVERY session
1. `docs/ENGINEERING_SPEC.md` — the full engineering constitution (stack, system design, content model, URL scheme, security, DevOps, testing, milestones, working rules). **Every section applies. Read it completely.**
2. `docs/TZ_concept_ru.md` — the official Technical Specification (Russian). On any conflict the TZ wins.
3. `PROGRESS.md` — if it exists, resume from the first unfinished item.
4. `AUTOPILOT_PROMPT.md` — autopilot rules and per-milestone exit gates.

## Non-negotiables (summary; details in the spec)
- Stack: Python 3.12, Django 5.1, Wagtail 6, wagtail-localize, PostgreSQL 16, Redis 7, Celery, HTMX 2, Alpine 3, Tailwind 3, Docker Compose, nginx, GitHub Actions. No SPA, no swapping the stack.
- Two sections (🎗 women: breast & cervical cancer; 🎀 children), one navigation, distinct colour identity each.
- Bilingual `uz` (default, Latin) + `ru`. No hard-coded UI text.
- 100 % of the TZ: every page, table cell and bullet — tracked in `docs/TZ_TRACE.md`.
- Never write medical content; seed placeholders `[[TODO: content — copywriter]]` / `[[VERIFY: doctor]]`.
- Mobile-first, 3G, WCAG 2.1 AA, PII encrypted, data stays on servers in Uzbekistan, 2FA on CMS.
- `make check` green before and after every change; small Conventional Commits; update `PROGRESS.md` continuously.
- Narrate to the developer in Uzbek; code, identifiers, commits, dev docs in English; editor docs in ru + uz.
