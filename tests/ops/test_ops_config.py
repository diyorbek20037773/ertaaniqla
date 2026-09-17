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
    assert "^/(uz|oz|ru)/(savol-javob" in site  # form rate zone covers the Cyrillic version
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
        "sonarqube",
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


# --- CI/CD + observability additions (ADR-0005) ---------------------------------------------------


def test_sonarqube_gate_in_ci_and_self_hosted_server() -> None:
    ci = _yaml(".github/workflows/ci.yml")
    jobs = ci["jobs"]
    sonar = jobs["sonarqube"]
    assert sonar["needs"] == ["quality"]
    assert "SONAR_HOST_URL" in sonar["if"]  # skipped until the server is configured
    steps = " ".join(str(s) for s in sonar["steps"])
    assert "sonarqube-scan-action" in steps and "qualitygate.wait=true" in steps
    assert "coverage" in steps  # imports coverage.xml from `quality`
    # a red gate blocks the image; a skipped (unconfigured) gate does not
    assert "sonarqube" in jobs["build"]["needs"]
    assert "failure" in jobs["build"]["if"]
    for deploy in ("deploy-staging", "deploy-prod"):
        assert ".result == 'success'" in jobs[deploy]["if"], deploy

    props = (ROOT / "sonar-project.properties").read_text(encoding="utf-8")
    assert "sonar.projectKey=ertaaniqla" in props
    assert "sonar.python.coverage.reportPaths=coverage.xml" in props
    assert "**/migrations/**" in props

    compose = _yaml("compose.sonarqube.yml")
    services = compose["services"]
    assert services["sonarqube"]["image"].endswith("-community")
    assert "ports" not in services["sonarqube"]  # reachable only through nginx
    assert "prod" in services["sonarqube"]["networks"]
    assert services["sonar-db"]["image"] == "postgres:16-alpine"

    site = (ROOT / "docker/nginx/templates/ertaaniqla.conf.template").read_text(encoding="utf-8")
    assert "server_name ${SONAR_DOMAIN};" in site
    assert "set $sonar http://${SONAR_UPSTREAM};" in site  # lazy upstream: nginx starts without it
    assert "vm.max_map_count = 524288" in (ROOT / "scripts/bootstrap_vps.sh").read_text(
        encoding="utf-8"
    )


def test_local_stage_hooks_and_targets() -> None:
    hooks = _yaml(".pre-commit-config.yaml")
    assert set(hooks["default_install_hook_types"]) == {"pre-commit", "pre-push"}
    pre_push = [
        h for repo in hooks["repos"] for h in repo["hooks"] if "pre-push" in h.get("stages", [])
    ]
    assert pre_push and "pytest" in pre_push[0]["entry"] and "mypy" in pre_push[0]["entry"]
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert re.search(r"^ci-local: check frontend build", makefile, re.M)
    assert re.search(r"^sonar:", makefile, re.M) and re.search(r"^sonar-up:", makefile, re.M)


def test_logs_and_traces_stack() -> None:
    services = _yaml("compose.prod.yml")["services"]
    for name in ("loki", "alloy", "jaeger", "monitoring-init"):
        assert services[name]["profiles"] == ["monitoring"], name
    assert services["jaeger"]["ports"] == ["127.0.0.1:16686:16686"]  # SSH tunnel only
    assert "ports" not in services["loki"] and "ports" not in services["alloy"]
    assert "/var/run/docker.sock:/var/run/docker.sock:ro" in services["alloy"]["volumes"]
    for app in ("web", "worker", "beat"):
        env = services[app]["environment"]
        assert env["OTEL_TRACES_SAMPLER"].endswith("parentbased_traceidratio}"), app
        assert env["OTEL_LOGS_EXPORTER"] == "none", app

    loki = _yaml("docker/monitoring/loki.yml")
    assert loki["limits_config"]["retention_period"] == "720h"
    assert loki["compactor"]["retention_enabled"] is True
    assert loki["ruler"]["alertmanager_url"] == "http://alertmanager:9093"
    rules = _yaml("docker/monitoring/loki-rules/fake/audit.yml")
    names = {r["alert"] for g in rules["groups"] for r in g["rules"]}
    assert {"CmsAccountLockout", "CmsLoginFailuresSpike", "PrivilegeChange"} <= names

    jaeger = _yaml("docker/monitoring/jaeger.yml")
    assert jaeger["receivers"]["otlp"]["protocols"]["http"]["endpoint"] == "0.0.0.0:4318"
    assert jaeger["extensions"]["jaeger_storage"]["backends"]["badger_store"]["badger"]["ttl"] == {
        "spans": "168h"
    }

    alloy = (ROOT / "docker/monitoring/alloy.config").read_text(encoding="utf-8")
    assert 'loki.source.docker "containers"' in alloy
    assert "[redacted]" in alloy  # secrets masked before shipping


def test_grafana_logs_audit_dashboard_and_loki_datasource() -> None:
    import json

    datasource = _yaml("docker/monitoring/grafana/provisioning/datasources/loki.yml")
    loki = datasource["datasources"][0]
    assert loki["uid"] == "loki"
    assert "trace_id" in loki["jsonData"]["derivedFields"][0]["matcherRegex"]
    dashboard = json.loads(
        (ROOT / "docker/monitoring/grafana/dashboards/ertaaniqla-logs-audit.json").read_text(
            encoding="utf-8"
        )
    )
    assert dashboard["uid"] == "ertaaniqla-logs-audit"
    exprs = " ".join(t["expr"] for p in dashboard["panels"] for t in p["targets"])
    for event in ("auth.login_failed", "auth.lockout", "user.superuser_changed"):
        assert event in exprs, event
