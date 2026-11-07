"""Deterministic offline demonstration assessment, intentionally labelled fixture data."""
import json
from datetime import datetime, timezone
from .config import FIXTURE_DIR

def demo(payload, route, windows):
    fixture=json.loads((FIXTURE_DIR/"demo_assessment.json").read_text())
    fixture["route"]={**route,"date":payload["date"],"departure_local":payload["departure_time"],"estimated_duration_hours":payload["duration_hours"],
                      "estimated_arrival_local":windows["arrival_local"].isoformat(timespec="minutes")}
    fixture["source_status"][0]["scope"]=f"{route['origin']}–{route['destination']} route"
    fixture["checked_at"]=datetime.now(timezone.utc).isoformat(timespec="seconds")
    fixture["assumptions"].append("Evidence values are bundled illustrative fixtures, not live conditions.")
    return fixture
