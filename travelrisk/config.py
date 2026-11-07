from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
STATIC_DIR = ROOT / "static"
CACHE_DIR = DATA_DIR / "cache"
FIXTURE_DIR = DATA_DIR / "fixtures"
SETTINGS_PATH = ROOT / "config" / "settings.json"
SETTINGS = json.loads(SETTINGS_PATH.read_text())
AIRPORTS = json.loads((DATA_DIR / "airports.json").read_text())
