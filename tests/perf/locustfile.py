"""Load test (spec §12): 200 users for 5 minutes, no errors, p95 < 300 ms for cached pages.

Anonymous visitor mix, weighted like the expected traffic: mostly article/section reads in both
languages, some search (HTMX search-as-you-type + full page), directory filters and tools.

    # against a production-settings container (see docs/LAUNCH_CHECKLIST.md "Load test")
    uv run locust -f tests/perf/locustfile.py --host http://localhost:8002 \
        --headless -u 200 -r 20 -t 5m --csv .locust/run --html .locust/report.html

`X-Forwarded-Proto: https` mimics nginx so production settings do not redirect to TLS.
Not collected by pytest (file name does not match test_*.py).
"""

from __future__ import annotations

import random
from typing import Any

from locust import HttpUser, between, events, task

HEADERS = {
    "X-Forwarded-Proto": "https",
    "Accept-Language": "uz,ru;q=0.8",
    "User-Agent": "ertaaniqla-locust/1.0",
}

READ_PAGES = [
    "/uz/",
    "/ru/",
    "/uz/ayollar/",
    "/ru/zhenskiy/",
    "/uz/bolalar/",
    "/ru/detskiy/",
    "/uz/ayollar/ogohlik/kokrak-bezi-saratoni/",
    "/ru/zhenskiy/osvedomlennost/rak-molochnoy-zhelezy/",
    "/uz/ayollar/skrining/kokrak-bezi-saratoni/",
    "/ru/zhenskiy/skrining/rak-molochnoy-zhelezy/",
    "/uz/ayollar/davolash/",
    "/uz/bolalar/parvarish/",
    "/uz/hikoyalar/",
    "/ru/istorii/",
    "/uz/lugat/",
    "/ru/slovar/",
    "/uz/savol-javob/",
    "/uz/materiallar/",
]
SEARCH_TERMS = ["saraton", "skrining", "рак", "маммография", "ko'krak", "bolalar", "leykoz"]
REGIONS = ["", "tashkent-city", "samarkand", "fergana", "karakalpakstan"]
TOOLS = ["/uz/vositalar/skrining/", "/ru/instrumenty/skrining/", "/uz/vositalar/oz-tekshiruv/"]


class Visitor(HttpUser):
    wait_time = between(1, 5)  # people read; a 3G page view is not a hammer

    def on_start(self) -> None:
        self.client.headers.update(HEADERS)

    @task(10)
    def read_page(self) -> None:
        path = random.choice(READ_PAGES)
        self.client.get(path, name="page")

    @task(2)
    def search_as_you_type(self) -> None:
        term = random.choice(SEARCH_TERMS)
        for length in range(3, len(term) + 1, 2):
            self.client.get(
                f"/uz/qidiruv/?q={term[:length]}",
                headers={"HX-Request": "true"},
                name="search (htmx)",
            )
        self.client.get(f"/uz/qidiruv/?q={term}", name="search (page)")

    @task(2)
    def directory_filter(self) -> None:
        region = random.choice(REGIONS)
        self.client.get("/uz/ayollar/qayerga-murojaat/", name="directory")
        self.client.get(
            f"/uz/ayollar/qayerga-murojaat/?region={region}",
            headers={"HX-Request": "true"},
            name="directory filter (htmx)",
        )

    @task(1)
    def tool(self) -> None:
        self.client.get(random.choice(TOOLS), name="tool")

    @task(1)
    def health(self) -> None:
        self.client.get("/healthz/", name="healthz")


@events.quitting.add_listener
def enforce_budgets(environment: Any, **_kwargs: Any) -> None:
    """Exit code 1 when the spec §12 budget is broken: any error, or page p95 ≥ 300 ms."""
    stats = environment.stats
    page = stats.get("page", "GET")
    failures = stats.total.fail_ratio
    p95 = page.get_response_time_percentile(0.95) if page.num_requests else 0
    if failures > 0 or p95 >= 300:
        environment.process_exit_code = 1
    print(
        f"budget: fail_ratio={failures:.4f} page_p95={p95} ms "
        f"→ {'FAIL' if environment.process_exit_code else 'OK'}"
    )
