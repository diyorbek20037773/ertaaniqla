"""wagtail-localize fixes for our blocks (D-094).

`StreamFieldSegmentExtractor.handle_image_block` (wagtail-localize 1.14) calls `.get()` on the raw
value of a Wagtail ImageBlock, which is None when an optional image is left empty — every text
card without a picture. «Translate this page» then fails with HTTP 500 on the women's pages. An
empty image has nothing to translate, so it yields no segments. Remove once upstream handles it.
"""

from __future__ import annotations

from typing import Any


def patch_image_block_extraction() -> None:
    from wagtail_localize.segments.extract import StreamFieldSegmentExtractor

    original = StreamFieldSegmentExtractor.handle_image_block
    if getattr(original, "_erta_aniqla_patch", False):
        return

    def handle_image_block(
        self: Any, block: Any, image_block_value: Any, raw_value: Any = None
    ) -> list[Any]:
        if image_block_value is None and not raw_value:
            return []  # an optional image left empty
        result: list[Any] = original(self, block, image_block_value, raw_value or {})
        return result

    handle_image_block._erta_aniqla_patch = True  # type: ignore[attr-defined]
    StreamFieldSegmentExtractor.handle_image_block = handle_image_block
