"""Search view: `/uz/qidiruv/?q=` and `/ru/poisk/?q=`. HTMX requests get the results partial;
plain GET renders the full page (non-JS fallback, spec §5)."""

from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils.translation import get_language
from django.views.decorators.http import require_GET

from apps.search.services import MAX_QUERY_LENGTH, clean_query, search_pages


@require_GET
def search(request: HttpRequest) -> HttpResponse:
    raw = request.GET.get("q", "")
    query = clean_query(raw)
    language = get_language() or "uz"
    results = search_pages(query, language) if query else []
    context = {
        "query": query,
        "raw_query": raw[:MAX_QUERY_LENGTH],
        "results": results,
        "result_count": len(results),
        "max_query_length": MAX_QUERY_LENGTH,
    }
    template = "search/_results.html" if request.headers.get("HX-Request") else "search/search.html"
    response = render(request, template, context)
    response["Vary"] = "HX-Request, Accept-Language, Cookie"
    return response
