"""Block rendering helpers."""

from __future__ import annotations

from typing import Any

from django import template

from apps.articles.blocks import link_href as _link_href

register = template.Library()


@register.filter
def link_href(value: Any) -> str:
    return _link_href(value)


def _is_all_caps(text: str) -> bool:
    """A title the designer typed in capitals (Figma «PAST MALIGNLIK») — set larger by the CSS."""
    letters = [c for c in text if c.isalpha()]
    return len(letters) >= 4 and not any(c.islower() for c in letters)


@register.filter
def resolve_step_links(steps: Any) -> list[dict[str, Any]]:
    """StepBlock values → plain dicts with a resolved `href` for components/steps.html."""
    return [
        {
            "number": step.get("number") or "",
            "title": step.get("title"),
            "caps": _is_all_caps(step.get("title") or ""),
            "text": step.get("text"),
            "deadline": step.get("deadline") or "",
            "href": _link_href(step.get("link")),
        }
        for step in steps
    ]


@register.filter
def illustration_src(name: str | None) -> str:
    """Static URL of a designer icon/illustration name (apps.articles.illustrations), or ""."""
    from django.templatetags.static import static

    from apps.articles.illustrations import static_path

    path = static_path(name or "")
    return static(path) if path else ""
