# ADR-0004 — Production operations on a single VPS

Status: accepted · Date: 2026-09-16 · Milestone: M6

## Context

Spec §11 asks for a production setup a single developer can operate: nginx + TLS, resource
limits, backups with a tested restore, monitoring with Telegram alerts, staging, CI/CD with
zero-downtime deploys and rollback, and a ≤ 1 h rebuild path. Data must stay in Uzbekistan.

## Decision

1. **One VPS, two compose projects** (`ertaaniqla-prod`, `ertaaniqla-staging`) from the same
   `compose.yml` + `compose.prod.yml` (+ `compose.staging.yml`). Only prod publishes 80/443;
   its nginx also serves `staging.<domain>` behind basic auth (D-037).
2. **nginx official image + envsubst templates** (D-033): no custom build; gzip only (brotli
   deferred, H-015); micro-cache 10 s for anonymous HTML; rate zones; media/video rules; raw
   uploads and Wagtail documents never served directly.
3. **TLS**: certbot webroot with a self-signed placeholder for the first start
   (`init_letsencrypt.sh`), renewal container + `nginx-reloader` (D-039).
4. **Backups** (D-034/D-035): `pg_dump -Fc` + restic (dump + media) nightly to a repository in
   UZ, 7d/4w/6m, `restic check`; weekly automated restore test into a scratch database;
   Prometheus textfile metrics → `BackupTooOld` / `RestoreTestTooOld` alerts.
5. **Monitoring** (D-036): compose profile with Prometheus, Alertmanager (Telegram), Grafana
   (SSH tunnel), nginx/postgres/redis/node/blackbox exporters; dashboards and rules in git.
6. **CI/CD**: build → trivy → SBOM → `nginx -t` + compose/promtool/amtool checks → deploy
   staging (auto) → deploy prod (GitHub environment approval) → smoke → Telegram; rollback
   and weekly base-image rebuild workflows; Dependabot.
7. **Postgres client 16 pinned** in the image from PGDG (D-038).
8. Runbook (`docs/RUNBOOK.md`) and threat model (`docs/SECURITY.md`) are the operating
   documents; every procedure in the runbook was executed once during M6.

## Consequences

* Everything lives in git; a new VPS is `scripts/bootstrap_vps.sh` + `.env` + restore.
* The backup container has no docker socket, so the weekly test restores into a scratch
  *database*; a scratch *container* restore is the documented quarterly drill.
* Monitoring shares the VPS: a full host outage is only visible through an external check
  (H-016).
* Brotli, Loki, ZAP and an nginx-level query allow-list are tracked in `TODO_HARDENING.md`.
