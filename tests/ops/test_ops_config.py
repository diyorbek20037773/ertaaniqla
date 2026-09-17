"""Static checks on the ops layer (spec §11): compose files, nginx config, alert rules,
`.env.example` completeness. Runtime checks (`nginx -t`, `compose config`, backup → restore)
run in CI (`build` job) and via `make ops-check` — they need Docker."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]


def _yaml(rel: str) -> dict:
    return yaml.safe_load((ROOT / rel).read_text(encoding="utf-8"))


def test_env_example_documents_every_setting() -> None:
    """Every `env("NAME"` / `env.int("NAME"` read in config/settings must be in .env.example."""
    used: set[str] = set()
    for path in (ROOT / "config" / "settings").glob("*.py"):
        used |= set(
            re.findall(r'env(?:\.\w+)?\(\s*"([A-Z0-9_]+)"', path.read_text(encoding="utf-8"))
        )
    documented = set(
        re.findall(r"^([A-Z0-9_]+)=", (ROOT / ".env.example").read_text(encoding="utf-8"), re.M)
    )
    missing = sorted(used - documented)
    assert not missing, f"undocumented in .env.example: {missing}"


def test_prod_compose_shape() -> None:
    prod = _yaml("compose.prod.yml")
    services = prod["services"]
    for name in (
        "nginx",
        "certbot",
        "backup",
        "prometheus",
        "alertmanager",
        "grafana",
        "node-exporter",
    ):
        assert name in services, name
    assert services["web"]["deploy"]["resources"]["limits"]["memory"] == "4g"
    assert services["db"]["deploy"]["resources"]["limits"]["memory"] == "4g"
    assert services["worker"]["deploy"]["resources"]["limits"]["memory"] == "2g"
    assert "shared_buffers=2GB" in services["db"]["command"]
    for name, svc in services.items():
        assert svc.get("logging", {}).get("options", {}).get("max-size") == "50m", name
    for name in ("prometheus", "grafana", "alertmanager", "nginx-exporter"):
        assert services[name]["profiles"] == ["monitoring"], name
    assert services["nginx"]["ports"] == ["80:80", "443:443"]
    assert services["grafana"]["ports"] == ["127.0.0.1:3000:3000"]  # SSH tunnel only


def test_staging_compose_publishes_nothing() -> None:
    staging = _yaml("compose.staging.yml")
    for name in ("nginx", "certbot", "nginx-reloader"):
        assert staging["services"][name]["profiles"], name
    assert "prod" in staging["services"]["web"]["networks"]


def test_nginx_config_requirements() -> None:
    main = (ROOT / "docker/nginx/nginx.conf").read_text(encoding="utf-8")
    site = (ROOT / "docker/nginx/templates/ertaaniqla.conf.template").read_text(encoding="utf-8")
    snippets = "".join(
        p.read_text(encoding="utf-8") for p in (ROOT / "docker/nginx/snippets").glob("*.conf")
    )
    # rate zones (spec §11.2)
    assert "zone=general:10m rate=30r/s" in main
    assert "zone=cms_login:10m rate=5r/m" in main
    assert "zone=form_post:10m rate=10r/m" in main
    assert "return 444" in main  # unknown hosts
    assert "proxy_cache_path" in main and "proxy_cache_valid 200 301 302 10s" in site
    # upload limits
    assert "client_max_body_size 2m" in main
    assert re.search(r"location \^~ /cms/ \{[^}]*client_max_body_size 512m", site, re.S)
    # TLS + headers
    assert "ssl_protocols TLSv1.2 TLSv1.3" in snippets and "ssl_stapling on" in snippets
    assert "Strict-Transport-Security" in snippets and "Referrer-Policy" in snippets
    assert "Content-Security-Policy" not in snippets  # CSP is Django's (nonce)
    # static / media / video
    assert "expires 1y" in snippets and "immutable" in snippets
    assert "expires 30d" in snippets and "mp4;" in snippets
    assert "location ^~ /media/documents/     { return 404; }" in snippets
    assert "location ^~ /media/videos/source/ { return 404; }" in snippets
    # maintenance flag, health endpoints, staging vhost
    assert "maintenance.flag" in site and "return 503" in site
    # alternate hosts (www., oncoportal.uz — TZ §IV) → canonical domain
    assert "server_name ${DOMAIN_ALT};" in site
    assert "return 301 https://${DOMAIN}$request_uri;" in site
    assert "location = /healthz/" in site and "location = /readyz/" in site
    assert "auth_basic_user_file /etc/nginx/staging.htpasswd" in site
    # anonymised access log
    assert "$remote_addr_anon" in main


def test_alert_rules_cover_spec() -> None:
    rules = _yaml("docker/monitoring/alert_rules.yml")
    names = {r["alert"] for g in rules["groups"] for r in g["rules"]}
    for expected in (
        "High5xxRate",
        "HighLatencyP95",
        "DiskAlmostFull",
        "BackupTooOld",
        "CertificateExpiringSoon",
        "CeleryQueueBacklog",
        "SiteDown",
    ):
        assert expected in names, expected


def test_prometheus_scrapes_every_exporter() -> None:
    cfg = _yaml("docker/monitoring/prometheus.yml")
    jobs = {j["job_name"] for j in cfg["scrape_configs"]}
    assert {"django", "nginx", "postgres", "redis", "node", "blackbox-https"} <= jobs


def test_grafana_dashboard_is_provisioned() -> None:
    import json

    dashboard = json.loads(
        (ROOT / "docker/monitoring/grafana/dashboards/ertaaniqla-overview.json").read_text(
            encoding="utf-8"
        )
    )
    assert dashboard["uid"] == "ertaaniqla-overview" and len(dashboard["panels"]) >= 12
    provisioning = _yaml("docker/monitoring/grafana/provisioning/dashboards/dashboards.yml")
    assert provisioning["providers"][0]["options"]["path"] == "/var/lib/grafana/dashboards"


@pytest.mark.parametrize(
    "script",
    [
        "docker/scripts/backup.sh",
        "docker/scripts/restore.sh",
        "docker/scripts/restore_test.sh",
        "docker/scripts/backup_cron.sh",
        "docker/scripts/deploy.sh",
        "docker/scripts/smoke.sh",
        "docker/scripts/init_letsencrypt.sh",
        "docker/scripts/nginx_test.sh",
        "scripts/bootstrap_vps.sh",
    ],
)
def test_scripts_are_strict_bash(script: str) -> None:
    text = (ROOT / script).read_text(encoding="utf-8")
    assert text.startswith("#!/usr/bin/env bash\n")
    assert "set -euo pipefail" in text
    assert "\r" not in text  # LF only (runs on Linux)


def test_ci_pipeline_shape() -> None:
    ci = _yaml(".github/workflows/ci.yml")
    jobs = ci["jobs"]
    assert list(jobs) == [
        "quality",
        "frontend",
        "a11y-perf",
        "build",
        "deploy-staging",
        "deploy-prod",
    ]
    assert jobs["deploy-prod"]["environment"]["name"] == "prod"
    assert jobs["deploy-prod"]["needs"] == ["deploy-staging"]
    build_steps = " ".join(str(s) for s in jobs["build"]["steps"])
    assert "trivy" in build_steps and "sbom" in build_steps and "nginx_test.sh" in build_steps
    rollback = _yaml(".github/workflows/rollback.yml")
    assert rollback[True]["workflow_dispatch"]["inputs"]["tag"]["required"] is True
