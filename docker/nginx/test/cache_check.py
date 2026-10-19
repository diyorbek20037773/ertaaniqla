"""nginx micro-cache behaviour against a stub of Django's anonymous-HTML policy (D-093).

`python cache_check.py origin` serves what apps.core.cache does: a fresh CSP nonce per response,
`public, max-age=0, must-revalidate, s-maxage=10`, a weak ETag of the page without its nonce, and
a 304 without a CSP header on a matching If-None-Match. `python cache_check.py client <host>`
then talks HTTPS to the real nginx config (docker/scripts/nginx_cache_test.sh) and checks what a
browser gets. Standard library only (runs in python:3.12-alpine).
"""

from __future__ import annotations

import hashlib
import http.client
import re
import secrets
import ssl
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

POLICY = "public, max-age=0, must-revalidate, s-maxage=10"
DOMAIN = "ertaaniqla.uz"


class Origin(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args: object) -> None:
        pass

    def do_GET(self) -> None:
        if self.path == "/lang/":
            cookie = self.headers.get("Cookie", "")
            match = re.search(r"(?:^|;\s*)lang=([a-z_-]+)", cookie)
            body = f"lang={match.group(1) if match else '-'}".encode()
            return self._send(200, {"Cache-Control": POLICY, "Content-Type": "text/plain"}, body)
        nonce = secrets.token_urlsafe(16)
        page = f'<!doctype html><script nonce="{nonce}">ok()</script><p>{self.path}</p>'
        etag = 'W/"' + hashlib.sha256(page.replace(nonce, "").encode()).hexdigest()[:20] + '"'
        headers = {"Cache-Control": POLICY, "ETag": etag, "Content-Type": "text/html"}
        sent = self.headers.get("If-None-Match", "")
        tags = [t.strip().removeprefix("W/") for t in sent.split(",")]
        if etag.removeprefix("W/") in tags:
            return self._send(304, headers)  # Django's 304: no CSP (apps.core.cache._not_modified)
        headers["Content-Security-Policy"] = f"script-src 'self' 'nonce-{nonce}'"
        return self._send(200, headers, page.encode())

    def _send(self, status: int, headers: dict[str, str], body: bytes = b"") -> None:
        self.send_response(status)
        for name, value in headers.items():
            self.send_header(name, value)
        if status != 304:
            self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if status != 304:
            self.wfile.write(body)


def get(host: str, path: str, **headers: str) -> tuple[int, dict[str, str], str]:
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    conn = http.client.HTTPSConnection(host, 443, context=context, timeout=10)
    conn.request("GET", path, headers={"Host": DOMAIN, **headers})
    response = conn.getresponse()
    body = response.read().decode()
    conn.close()
    return response.status, {k.lower(): v for k, v in response.getheaders()}, body


def nonce_of(headers: dict[str, str]) -> str:
    match = re.search(r"'nonce-([^']+)'", headers.get("content-security-policy", ""))
    return match.group(1) if match else ""


def client(host: str) -> int:
    failures: list[str] = []

    def check(ok: bool, what: str) -> None:
        print(("ok   " if ok else "FAIL ") + what)
        if not ok:
            failures.append(what)

    for _ in range(30):  # nginx and the origin start in parallel
        try:
            get(host, "/healthz/")
            break
        except OSError:
            time.sleep(1)

    status, first, body = get(host, "/uz/page/")
    nonce = nonce_of(first)
    check(status == 200 and bool(nonce) and f'nonce="{nonce}"' in body, "200 carries its CSP nonce")
    check(first.get("x-content-type-options") == "nosniff", "security headers on HTML")
    etag = first.get("etag", "")
    check(etag.startswith('W/"'), "weak ETag passed through")
    status, again, body = get(host, "/uz/page/")
    check(nonce_of(again) == nonce and f'nonce="{nonce}"' in body, "micro-cache serves the copy")

    status, revalidated, body = get(host, "/uz/page/", **{"If-None-Match": etag})
    check(status == 304, "If-None-Match → 304")
    check("content-security-policy" not in revalidated, "304 from the cache has no CSP")
    check(revalidated.get("x-content-type-options") == "nosniff", "security headers on the 304")

    time.sleep(11)  # the 10 s entry expires; the next request refreshes it with a new nonce
    get(host, "/uz/page/")
    time.sleep(1)
    status, refreshed, _body = get(host, "/uz/page/")
    check(nonce_of(refreshed) not in ("", nonce), "refreshed entry has a new nonce")
    status, revalidated, _body = get(host, "/uz/page/", **{"If-None-Match": etag})
    check(status == 304, "same ETag after the refresh → 304")
    check(
        "content-security-policy" not in revalidated,
        "304 never carries the newer entry's CSP (the old copy's inline code keeps running)",
    )

    _s, _h, ru = get(host, "/lang/", Cookie="lang=ru")
    _s, _h, uz = get(host, "/lang/", Cookie="csrftoken_x=1; lang=uz")
    check(ru == "lang=ru" and uz == "lang=uz", "the `lang` cookie is part of the cache key")
    _s, _h, other = get(host, "/lang/", Cookie="django_language=ru")
    check(other == "lang=-", "another cookie ending in «language» is not the language")

    print("nginx cache test:", "FAILED" if failures else "OK")
    return 1 if failures else 0


if __name__ == "__main__":
    if sys.argv[1] == "origin":
        ThreadingHTTPServer(("0.0.0.0", 8000), Origin).serve_forever()
    sys.exit(client(sys.argv[2]))
