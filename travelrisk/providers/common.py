from datetime import datetime, timezone
from ..models import Evidence, SourceStatus

def now(): return datetime.now(timezone.utc).isoformat(timespec="seconds")

def status(source, scope, state, message, meta=None):
    meta = meta or {}
    if meta.get("cache") == "stale":
        message += f" Using last successful cached response from {meta.get('age_seconds', 0)} seconds ago after a live request failed."
    return SourceStatus(source, scope, state, message, now(), meta.get("age_seconds") if meta.get("cache") == "stale" else None)

def evidence(source, title, detail, url, observed=None, severity="info", *, signal_id="", meta=None):
    meta = meta or {}; stale = meta.get("cache") == "stale"
    return Evidence(source, title, detail, url, observed, severity, signal_id or title, stale,
                    meta.get("age_seconds") if stale else None)

def failed(source, scope, url, error):
    unsupported=getattr(error,"status_code",None)==404
    state="unsupported" if unsupported else "failed"
    message="This source does not cover this location or endpoint." if unsupported else "Request failed; no current result is available."
    return ([evidence(source, f"{source} {'does not cover this location' if unsupported else 'request failed'}", str(error)[:220], url, severity="unknown")],
            status(source, scope, state, message))
