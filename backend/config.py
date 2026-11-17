"""
Configuration settings for Congress Civic Analytics
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = DATA_DIR / "cache"
OUTPUT_DIR = BASE_DIR / "output"
VIDEOS_DIR = OUTPUT_DIR / "videos"
CARDS_DIR = OUTPUT_DIR / "cards"

# Ensure runtime directories exist
for d in [DATA_DIR, CACHE_DIR, OUTPUT_DIR, VIDEOS_DIR, CARDS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# API Keys & Deployment Security (configured via environment variables or .env)
CONGRESS_API_KEY = os.environ.get("CONGRESS_API_KEY", "").strip()
CENSUS_API_KEY = os.environ.get("CENSUS_API_KEY", "").strip()
FEC_API_KEY = os.environ.get("FEC_API_KEY", "").strip()

# Public-exposure protection settings (recommended when running behind Cloudflare Tunnel)
ADMIN_API_KEY = os.environ.get("ADMIN_API_KEY", "").strip()
ALLOWED_ORIGINS = [
    o.strip() for o in os.environ.get(
        "ALLOWED_ORIGINS",
        "http://localhost:8000,http://127.0.0.1:8000"
    ).split(",") if o.strip()
]

# Voice synthesis settings
DEFAULT_VOICE = os.environ.get("CONGRESS_TTS_VOICE", "en-US-ChristopherNeural")  # Deep energetic sports-anchor voice
FALLBACK_VOICES = ["en-US-GuyNeural", "en-US-EricNeural", "en-US-JennyNeural"]

# Policy Categories for Vote Breakdown
POLICY_CATEGORIES = [
    "Economy & Taxation",
    "Defense & National Security",
    "Healthcare & Medicare",
    "Energy & Environment",
    "Technology & AI / Privacy",
    "Immigration & Border Security",
    "Agriculture & Rural Development",
    "Infrastructure & Transportation",
    "Education & Labor",
    "Judiciary & Civil Rights",
    "Foreign Affairs & Trade",
    "Government Ethics & Spending"
]
