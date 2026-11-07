"""Small HTTP client with timeout, cache, and explicit stale fallback metadata."""
import hashlib, json, time, urllib.request, urllib.error, os, threading
from pathlib import Path
from .config import CACHE_DIR, SETTINGS

USER_AGENT = f"TripSignal/0.2 (public-data travel risk prototype; contact: {os.getenv('CONTACT_EMAIL','not-configured')})"
CACHE_LOCK = threading.Lock()

class FetchError(RuntimeError):
    def __init__(self,message,status_code=None):
        super().__init__(message); self.status_code=status_code

def _cache_path(url: str) -> Path:
    return CACHE_DIR / (hashlib.sha256(url.encode()).hexdigest() + ".json")

def fetch(url: str, *, accept: str = "application/json", ttl: int | None = None):
    """Return (payload, metadata); cached values are explicitly marked when stale."""
    path = _cache_path(url); now = time.time(); ttl = ttl or SETTINGS["source_cache_ttl_seconds"]
    if path.exists():
        try:
            saved = json.loads(path.read_text())
            age = max(0, int(now - saved["fetched_at"]))
            if age <= ttl:
                return saved["payload"], {"cache": "fresh", "age_seconds": age}
        except (OSError, ValueError, KeyError): pass
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": accept})
    try:
        with urllib.request.urlopen(req, timeout=SETTINGS["request_timeout_seconds"]) as response:
            if response.status == 204: return None, {"cache":"none","no_data":True,"age_seconds":0}
            raw = response.read()
            content_type = response.headers.get("Content-Type", "")
        if "json" in content_type or "geo+json" in content_type or accept == "application/json":
            payload = json.loads(raw.decode("utf-8", "replace"))
        else:
            payload = raw.decode("utf-8", "replace")
        path.parent.mkdir(parents=True, exist_ok=True)
        temp=path.with_suffix(f".{os.getpid()}.{threading.get_ident()}.tmp")
        with CACHE_LOCK:
            temp.write_text(json.dumps({"fetched_at": now, "payload": payload}, ensure_ascii=False))
            temp.replace(path)
        return payload, {"cache": "network", "age_seconds": 0}
    except Exception as exc:
        if path.exists():
            try:
                saved = json.loads(path.read_text()); age = max(0, int(now - saved["fetched_at"]))
                return saved["payload"], {"cache": "stale", "age_seconds": age, "error": str(exc)[:180]}
            except (OSError, ValueError, KeyError): pass
        raise FetchError(str(exc),getattr(exc,"code",None)) from exc

def get_json(url: str, ttl: int | None = None): return fetch(url, accept="application/geo+json, application/json", ttl=ttl)
def get_xml(url: str, ttl: int | None = None): return fetch(url, accept="application/xml, text/xml", ttl=ttl)
