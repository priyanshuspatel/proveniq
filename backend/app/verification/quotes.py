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


def single_supported_label(quotation: str) -> str | None:
    found = [label for label in SUPPORTED_LABELS if label in quotation]
    kept: list[str] = []
    for label in found:
        if any(label != longer and label in longer and longer in quotation for longer in found):
            continue
        kept.append(label)
    if len(kept) != 1:
        return None
    return kept[0]
