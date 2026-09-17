# ADR-0005 — Code analysis, tracing, central logs and security audit

Status: accepted · Date: 2026-09-17 · Follows: ADR-0004

## Context

The developer asked for a full delivery pipeline in four stages:

1. **Local** — commit → test → build → push.
2. **CI** — SonarQube code analysis → tests → build → Docker image → registry → deployment manifests.
3. **CD** — GitOps (ArgoCD) syncing Kubernetes manifests.
4. **Monitoring** — tracing (Jaeger), central logging (ELK/EFK), audit.

ADR-0004 already covers most of stages 1–3 (pre-commit, `make check`, GitHub Actions quality →
build → trivy → SBOM → GHCR → SSH deploy with approval, rollback) and metrics + alerts in stage 4.
Spec §3 fixes Docker Compose on one VPS and forbids swapping the stack without an ADR.

**Developer decision (2026-09-17):** stay on Compose and fill the gaps; do **not** introduce
Kubernetes/ArgoCD. SonarQube must be **self-hosted** (code does not leave our servers).

## Decision

| Requested | Implemented as | Why not the literal tool |
|---|---|---|
| Local commit/test/build/push | `pre-commit` installs **pre-commit + pre-push** hooks (push runs ruff, mypy, pytest -x); `make ci-local` = `check` + `frontend` + `build` | — |
| SonarQube | `compose.sonarqube.yml` (SonarQube Community 26.9 + Postgres 16, own compose project) behind the prod nginx at `sonar.<DOMAIN>`; CI job `sonarqube` (after `quality`, imports `coverage.xml`, waits for the **quality gate**); `make sonar` for a local scan | — |
| Testing / Build / Image / Registry | unchanged (ADR-0004): pytest ≥ 85 %, pa11y, Lighthouse, buildx → trivy → SBOM → `ghcr.io/…/web:<sha>` | — |
| Manifests + ArgoCD + K8s | **not adopted.** The "manifest" is `compose.yml` + `compose.prod.yml` at the deployed git SHA; `deploy.sh` pulls the image tag and runs `up --wait` (staging automatic, prod approval); `rollback.yml` redeploys any tag | K8s needs ≥ 3 nodes, etcd, ingress, CSI storage, cert-manager and an operator — not one-person-operable for one Django site; spec §3/§11 |
| Tracing (Jaeger) | OpenTelemetry SDK in web/worker/beat (`apps/core/tracing.py`: Django, psycopg, Celery) → OTLP/HTTP → **Jaeger v2** all-in-one with Badger (7 d) in the `monitoring` profile; UI over SSH tunnel; `trace_id` in every JSON log line | — |
| Logging (ELK/EFK) | **Loki 3 + Grafana Alloy** (docker log discovery) in the `monitoring` profile, 30 d retention, secrets masked in the pipeline, Grafana datasource with `trace_id` → Jaeger links, dashboard "logs & audit" | Elasticsearch needs 2–4 GB heap on top of SonarQube's; Loki indexes labels only and reuses Grafana/Alertmanager we already run. Spec §3 already names Loki. Promtail is end-of-life → Alloy |
| Audit | `apps/core/audit.py`: logins, logouts, failed logins, lockouts, user/flag/password/role/permission/2FA changes, PII record views, mirror of all Wagtail CMS actions → `ertaaniqla.audit` JSON logger (→ Loki) **and** Wagtail log entries (CMS → Reports → Site history); Loki ruler alerts (lockout, login-failure spike, privilege change, error spike) → Alertmanager → Telegram | — |

Privacy rules (spec §8) hold for every new signal: spans never carry query strings, client IPs,
user agents or SQL parameters; audit lines carry `/24` (IPv4) or `/48` (IPv6) prefixes, never
passwords, OTP keys, decrypted contacts or unknown usernames (12-char hash instead). Loki, Jaeger
and SonarQube data stay on our server.

## Consequences

* New memory on the VPS (limits): Loki 1 GB, Jaeger 768 MB, Alloy 256 MB; SonarQube 3 GB + DB
  512 MB. On the 16 GB VPS SonarQube fits only because limits are caps, not reservations;
  if memory pressure appears, move `compose.sonarqube.yml` to a small second VM in UZ
  (nothing else changes: CI talks to `SONAR_HOST_URL`). `vm.max_map_count=524288` is set by
  `bootstrap_vps.sh`.
* CI stays green before SonarQube exists: the job is skipped while `vars.SONAR_HOST_URL` is empty;
  build/deploy conditions accept a skipped gate but never a failed one.
* Tracing costs nothing until `OTEL_EXPORTER_OTLP_ENDPOINT` is set; head sampling 10 %.
* Alloy is the second container with the docker socket (read-only, log discovery only).
* Jaeger v2 exposes only the `/api/v3` query API, which Grafana 11's Jaeger datasource does not
  read; traces are opened in the Jaeger UI through links from Loki (H-025).
* Revisit Kubernetes/GitOps only if the portal grows to several independently deployed services
  or needs multi-node HA (write ADR-0006 then).
