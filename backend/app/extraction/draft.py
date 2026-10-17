from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.verification.quotes import SUPPORTED_LABELS

RecognizedLicense = Literal[
    "CC0-1.0",
    "CC-BY-4.0",
    "CC-BY-SA-4.0",
    "CC-BY-NC-4.0",
    "CC-BY-NC-SA-4.0",
    "CC-BY-ND-4.0",
    "CC-BY-NC-ND-4.0",
    "all-rights-reserved",
    "UNKNOWN",
]


class ExtractionDraft(BaseModel):
    """Untrusted model draft. A compliance verdict is ignored. Quotations are required strings."""

    model_config = ConfigDict(extra="ignore")

    recognized_license: RecognizedLicense
    license_quotation: str
    creator: str | None = None
    creator_quotation: str
    license_url: str | None = None
    license_url_quotation: str
    attribution_instructions: str | None = None
    attribution_quotation: str


def draft_json_schema() -> dict:
    schema = ExtractionDraft.model_json_schema()
    schema.pop("title", None)
    return schema


assert set(SUPPORTED_LABELS).issubset(set(RecognizedLicense.__args__) - {"UNKNOWN"})
assert "license_quotation" in ExtractionDraft.model_json_schema()["required"]
