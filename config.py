import os
from dotenv import load_dotenv

load_dotenv()

URLS = [
    "https://www.placidway.com/profile/5/Alternative-Cancer-Treatment-by-ITC-Immunity-Therapy-Center",
    "https://www.placidway.com/package/7903/Alternative-Adenocarcinoma-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC",
    "https://www.placidway.com/package/7902/Alternative-Adrenal-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC",
    "https://www.placidway.com/package/7901/Alternative-Anal-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC",
    "https://www.placidway.com/profile-videos/5/Alternative-Cancer-Treatment-by-ITC-Immunity-Therapy-Center",
    "https://www.placidway.com/price-list/5/Alternative-Cancer-Treatment-by-ITC-Immunity-Therapy-Center",
    "https://www.placidway.com/search-medical-pricings/Alternative-Medicine/All/1",
]

USER_AGENT = "PLacidWayAssessmentBot/1.0 (candidate for assessment; contact: steven.fakayode@gamil.com)"
REQUEST_DELAY = 1.0  # seconds

INDEX_PATH = "data/index.json"
EMBED_MODEL = "BAAI/bge-small-en-v1.5"
TOP_K = 5
MIN_SCORE = 0.45

LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_BASE_URL = os.getenv("LLM_BASE_URL") or None
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
SHEETS_WEBHOOK_URL = os.getenv("SHEETS_WEBHOOK_URL")
SHEETS_TOKEN = os.getenv("SHEETS_TOKEN")

CONTACT_URL = "https://www.placidway.com/contact-us"
FALLBACK = (
    "I couldn't find that in the PlacidWay pages I have access to, so T don't want give you inaccurate information."
    f"For accurate information, please visit the PlacidWay contact page: {CONTACT_URL}"
)
DISCLAIMER = (
    "ℹ️ This information comes from PlacidWay's pages and is not medical advice. "
    "Please consult a qualified doctor before making treatment decisions."
)