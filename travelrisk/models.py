from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

@dataclass
class SourceStatus:
    source: str
    scope: str
    state: str  # data | clear | no_data | failed | unsupported | stale
    message: str
    checked_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))
    cache_age_seconds: int | None = None

@dataclass
class Evidence:
    source: str
    title: str
    detail: str
    url: str
    observed_at: str | None
    severity: str = "info"  # info | moderate | high | unknown
    signal_id: str = ""
    stale: bool = False
    cache_age_seconds: int | None = None
    def to_dict(self) -> dict[str, Any]: return asdict(self)

@dataclass
class Assessment:
    route: dict[str, Any]
    score: int | None
    band: str
    confidence: str
    action: str
    action_reasons: list[str]
    evidence: list[Evidence]
    source_status: list[SourceStatus]
    coverage: dict[str, Any]
    checked_at: str
    assumptions: list[str]
    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d
