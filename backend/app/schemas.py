from datetime import datetime
from enum import Enum
from urllib.parse import urlparse
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ReviewStatus(str, Enum):
    SUPPORTED_CHECKS_PASSED = "supported-checks-passed"
    POTENTIAL_CONFLICT = "potential-conflict"
    MISSING_INFORMATION = "missing-information"
    UNSUPPORTED_LICENSE = "unsupported-license"
    MANUAL_REVIEW_REQUIRED = "manual-review-required"


class IntendedUse(str, Enum):
    CLIENT_DELIVERY_AS_IS = "client-delivery-as-is"
    CLIENT_DELIVERY_MODIFIED = "client-delivery-modified"
    COMMERCIAL = "commercial"
    NONCOMMERCIAL = "noncommercial"


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _require_text(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError("must not be blank")
    return stripped


def _http_url(value: str | None) -> str | None:
    cleaned = _blank_to_none(value)
    if cleaned is None:
        return None
    parsed = urlparse(cleaned)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("source_url must be an absolute http or https URL")
    return cleaned


class ProjectCreate(ApiModel):
    name: str = Field(min_length=1, max_length=200)
    client_label: str | None = Field(default=None, max_length=200)
    declared_intended_use: IntendedUse

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, value: str) -> str:
        return _require_text(value)

    @field_validator("client_label")
    @classmethod
    def client_label_blank(cls, value: str | None) -> str | None:
        return _blank_to_none(value)


class ProjectRead(ProjectCreate):
    id: UUID
    created_at: datetime
    asset_count: int = Field(default=0, ge=0)
    review_status: ReviewStatus | None = None


class ProjectUpdate(ApiModel):
    name: str | None = Field(default=None, max_length=200)
    client_label: str | None = Field(default=None, max_length=200)
    declared_intended_use: IntendedUse | None = None

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _require_text(value)

    @field_validator("client_label")
    @classmethod
    def client_label_blank(cls, value: str | None) -> str | None:
        return _blank_to_none(value)


class AssetCreate(ApiModel):
    title: str = Field(min_length=1, max_length=300)
    creator: str | None = Field(default=None, max_length=200)
    source_url: str | None = Field(default=None, max_length=2048)
    declared_license: str = Field(min_length=1, max_length=120)
    supplied_license_text: str | None = Field(default=None, max_length=200_000)
    intended_use: IntendedUse | None = None
    attribution_text: str | None = Field(default=None, max_length=2000)

    @field_validator("title", "declared_license")
    @classmethod
    def required_text(cls, value: str) -> str:
        return _require_text(value)

    @field_validator("creator", "supplied_license_text", "attribution_text")
    @classmethod
    def optional_text(cls, value: str | None) -> str | None:
        return _blank_to_none(value)

    @field_validator("source_url")
    @classmethod
    def source_url_http(cls, value: str | None) -> str | None:
        return _http_url(value)


class AssetUpdate(ApiModel):
    title: str | None = Field(default=None, max_length=300)
    creator: str | None = Field(default=None, max_length=200)
    source_url: str | None = Field(default=None, max_length=2048)
    declared_license: str | None = Field(default=None, max_length=120)
    supplied_license_text: str | None = Field(default=None, max_length=200_000)
    intended_use: IntendedUse | None = None
    attribution_text: str | None = Field(default=None, max_length=2000)

    @field_validator("title", "declared_license")
    @classmethod
    def required_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _require_text(value)

    @field_validator("creator", "supplied_license_text", "attribution_text")
    @classmethod
    def optional_text(cls, value: str | None) -> str | None:
        return _blank_to_none(value)

    @field_validator("source_url")
    @classmethod
    def source_url_http(cls, value: str | None) -> str | None:
        return _http_url(value)


class AssetRead(AssetCreate):
    id: UUID
    project_id: UUID
    review_status: ReviewStatus


class HealthRead(ApiModel):
    status: str


class ErrorBody(ApiModel):
    code: str
    message: str
    details: list[dict[str, str]] = Field(default_factory=list)


class AnalyzeRequest(ApiModel):
    title: str = Field(min_length=1, max_length=300)
    asset_type: str | None = Field(default=None, max_length=80)
    creator: str | None = Field(default=None, max_length=200)
    source_url: str | None = Field(default=None, max_length=2048)
    license_text: str = Field(min_length=1, max_length=200_000)

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str) -> str:
        return _require_text(value)

    @field_validator("license_text", "creator", "asset_type")
    @classmethod
    def optional_or_text(cls, value: str | None) -> str | None:
        return _blank_to_none(value)

    @field_validator("license_text")
    @classmethod
    def license_text_required(cls, value: str | None) -> str:
        if value is None or not str(value).strip():
            raise ValueError("license text is required")
        return str(value).strip()

    @field_validator("source_url")
    @classmethod
    def source_url_http(cls, value: str | None) -> str | None:
        return _http_url(value)


class CheckedEvidence(ApiModel):
    field: str
    condition_type: str
    quotation: str
    verification_result: str
    quote_start: int | None = None
    quote_end: int | None = None
    confidence: float | None = None


class ReportCreate(ApiModel):
    asset_types: dict[UUID, str] = Field(default_factory=dict)

    @field_validator("asset_types")
    @classmethod
    def asset_types_are_short(cls, value: dict[UUID, str]) -> dict[UUID, str]:
        cleaned: dict[UUID, str] = {}
        for asset_id, asset_type in value.items():
            text = asset_type.strip()
            if not text:
                continue
            if len(text) > 80:
                raise ValueError("asset type must be 80 characters or fewer")
            cleaned[asset_id] = text
        return cleaned


class ReportRead(ApiModel):
    id: UUID
    project_id: UUID
    generated_at: datetime
    included_asset_ids: list[UUID]
    report_version: int = Field(ge=1)
    snapshot: dict
    disclaimer: str
    markdown: str
    included_asset_count: int = Field(default=0, ge=0)


class ReportSummaryRead(ApiModel):
    id: UUID
    project_id: UUID
    generated_at: datetime
    report_version: int = Field(ge=1)
    included_asset_count: int = Field(ge=0)


class AnalyzeRead(ApiModel):
    recognized_license: str
    creator: str | None
    user_supplied_creator: str | None = None
    license_url: str | None
    attribution_instructions: str | None
    uncertain_fields: list[str]
    evidence: list[CheckedEvidence]
    review_status: ReviewStatus
    extraction_note: str | None = None
