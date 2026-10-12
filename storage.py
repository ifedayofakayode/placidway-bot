import csv
import os
from datetime import datetime, timezone

import requests

import config

def _save(sheet, row):
    row = [datetime.now(timezone.utc).isoformat(timespec="seconds")] + row
    os.makedirs("data", exist_ok=True)
    with open(f"data/{sheet}.csv", "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(row)
    if config.SHEETS_WEBHOOK_URL:        # durable copy (free hosts forget local files)
        try:
            requests.post(config.SHEETS_WEBHOOK_URL, timeout=10,
                          json={"token": config.SHEETS_TOKEN, "sheet": sheet, "row": row})
        except requests.RequestException:
            pass


def log_unanswered(question, category, top_score):
    _save("unanswered", [question, category, top_score])


def save_lead(name, email, last_question):
    _save("leads", [name, email, last_question])