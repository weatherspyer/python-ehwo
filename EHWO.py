#!/usr/bin/env python3

import os
import json
import base64
import requests
import gspread
from datetime import datetime
from zoneinfo import ZoneInfo
from google.oauth2.service_account import Credentials

# ---------------- CONFIG ----------------

SHEET_ID = "18Ct-VfC83qDARC6sQYF4-XD0vCROeBP4hxdPhy--hAo"
SHEET_NAME = "Log"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets"
]

WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbxDYCUlAbJiID9ITPF4XMzoDHcuMxpjPUV-deIAOStO3zJFMdA8MTK8dy3pnMN6zCpN/exec"

# ----------------------------------------


def get_spreadsheet():

    creds_base64 = os.environ["GOOGLE_SHEETS_CREDENTIALS"]
    creds_json = base64.b64decode(creds_base64).decode("utf-8")
    creds_dict = json.loads(creds_json)

    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=SCOPES
    )

    client = gspread.authorize(creds)

    return client.open_by_key(SHEET_ID)


def get_timestamp():

    now_utc = datetime.now(ZoneInfo("UTC"))
    now_et = now_utc.astimezone(ZoneInfo("America/New_York"))

    return now_et.strftime("%Y-%m-%d %I:%M %p ET")


def main():

    timestamp = get_timestamp()

    spreadsheet = get_spreadsheet()
    sheet = spreadsheet.worksheet(SHEET_NAME)

    row = [
        timestamp,
        "EHWO Check",
        "Script Ran"
    ]

    sheet.insert_row(row, 2)

    print("✅ Row written to Google Sheets")

    # ----- Trigger webhook after sheet update -----

    try:
        response = requests.get(WEBHOOK_URL)

        if response.status_code == 200:
            print("📡 Webhook triggered successfully.")
        else:
            print(f"⚠️ Webhook failed: {response.status_code}")

    except Exception as e:
        print(f"🚨 Webhook error: {e}")


if __name__ == "__main__":
    main()
