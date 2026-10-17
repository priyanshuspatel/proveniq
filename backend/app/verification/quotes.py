"""Exact quotation checks against the supplied license text.

Matching uses Python string search, which counts Unicode code points. A quotation
is verified only when that exact string occurs once. Whitespace is not collapsed,
and the model is not asked to confirm its own quote.
"""

SUPPORTED_LABELS = (
    "CC-BY-NC-SA-4.0",
    "CC-BY-NC-ND-4.0",
    "CC-BY-NC-4.0",
    "CC-BY-ND-4.0",
    "CC-BY-SA-4.0",
    "CC-BY-4.0",
    "CC0-1.0",
    "all-rights-reserved",
)

# Published names for the same identifiers. Longer forms are listed first so
# "CC BY-NC 4.0" is not also read as "CC BY 4.0". A match is still an exact
# substring of the quotation; these strings are not substituted into the notice.
SURFACE_FORMS = (
    ("Attribution-NonCommercial-ShareAlike 4.0 International", "CC-BY-NC-SA-4.0"),
    ("Attribution-NonCommercial-NoDerivatives 4.0 International", "CC-BY-NC-ND-4.0"),
    ("Attribution-NonCommercial-ShareAlike 4.0", "CC-BY-NC-SA-4.0"),
    ("Attribution-NonCommercial-NoDerivatives 4.0", "CC-BY-NC-ND-4.0"),
    ("Attribution-NonCommercial 4.0 International", "CC-BY-NC-4.0"),
    ("Attribution-NoDerivatives 4.0 International", "CC-BY-ND-4.0"),
    ("Attribution-ShareAlike 4.0 International", "CC-BY-SA-4.0"),
    ("Attribution 4.0 International", "CC-BY-4.0"),
    ("CC BY-NC-SA 4.0", "CC-BY-NC-SA-4.0"),
    ("CC BY-NC-ND 4.0", "CC-BY-NC-ND-4.0"),
    ("CC BY-NC 4.0", "CC-BY-NC-4.0"),
    ("CC BY-ND 4.0", "CC-BY-ND-4.0"),
    ("CC BY-SA 4.0", "CC-BY-SA-4.0"),
    ("CC BY NC SA 4.0", "CC-BY-NC-SA-4.0"),
    ("CC BY NC ND 4.0", "CC-BY-NC-ND-4.0"),
    ("CC BY NC 4.0", "CC-BY-NC-4.0"),
    ("CC BY ND 4.0", "CC-BY-ND-4.0"),
    ("CC BY SA 4.0", "CC-BY-SA-4.0"),
    ("CC BY 4.0", "CC-BY-4.0"),
    ("CC0 1.0 Universal", "CC0-1.0"),
    ("CC0 1.0", "CC0-1.0"),
    ("All rights reserved", "all-rights-reserved"),
    ("all rights reserved", "all-rights-reserved"),
)


def locate_quote(source: str, quotation: str, model_start: int | None = None, model_end: int | None = None) -> tuple[str, int | None, int | None]:
    if quotation is None or quotation == "" or quotation.strip() == "":
        return "empty-quote", None, None
    start = source.find(quotation)
    if start < 0:
        return "not-found", None, None
    if source.find(quotation, start + 1) >= 0:
        return "ambiguous", None, None
    end = start + len(quotation)
    if model_start is not None or model_end is not None:
        if model_start != start or model_end != end:
            return "offset-mismatch", None, None
    return "verified", start, end


def _contained_by_longer_span(start: int, end: int, spans: list[tuple[int, int]]) -> bool:
    return any(other_start <= start and end <= other_end and (other_start, other_end) != (start, end) for other_start, other_end in spans)


def label_spans(quotation: str) -> list[tuple[str, str]]:
    """Return (canonical label, exact surface) for non-overlapping names in quotation."""
    raw: list[tuple[int, int, str, str]] = []
    for label in SUPPORTED_LABELS:
        start = 0
        while True:
            found = quotation.find(label, start)
            if found < 0:
                break
            raw.append((found, found + len(label), label, label))
            start = found + 1
    for surface, label in SURFACE_FORMS:
        start = 0
        while True:
            found = quotation.find(surface, start)
            if found < 0:
                break
            raw.append((found, found + len(surface), label, surface))
            start = found + 1
    spans = [(start, end) for start, end, _, _ in raw]
    kept: list[tuple[str, str]] = []
    seen: set[tuple[int, int, str]] = set()
    for start, end, label, surface in sorted(raw, key=lambda item: (item[0], -(item[1] - item[0]))):
        if _contained_by_longer_span(start, end, spans):
            continue
        key = (start, end, label)
        if key in seen:
            continue
        seen.add(key)
        kept.append((label, surface))
    return kept


def single_supported_label(quotation: str) -> str | None:
    labels = {label for label, _surface in label_spans(quotation)}
    if len(labels) != 1:
        return None
    return next(iter(labels))
