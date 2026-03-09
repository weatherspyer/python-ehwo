import requests
from PIL import Image
from io import BytesIO
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import math
from time import time
import os

# Selenium
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# -----------------------------
# CONFIG
# -----------------------------

SAVE_IMAGES = False

SHEET_ID = "18Ct-VfC83qDARC6sQYF4-XD0vCROeBP4hxdPhy--hAo"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# -----------------------------
# GOOGLE SHEETS AUTH
# -----------------------------

def get_spreadsheet():
    creds = Credentials.from_service_account_file(
        "credentials.json",
        scopes=SCOPES
    )
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID)

spreadsheet = get_spreadsheet()

# -----------------------------
# SELENIUM DAY TITLE SCRAPER
# -----------------------------

def update_day_titles(spreadsheet):
    try:
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        driver = webdriver.Chrome(options=options)
        driver.get("https://www.weather.gov/pbz/ehwo")

        day_th_elements = WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located(
                (By.XPATH, '//tr[@id="riskTitleRow"]/th[position()>1]')
            )
        )

        day_titles = [th.text.strip() for th in day_th_elements]

        driver.quit()

        if not day_titles:
            print("⚠️ Day titles not found")
            return

        print("📅 Day titles:", day_titles)

        sheet = spreadsheet.worksheet("Day_Names")

        for i, title in enumerate(day_titles, start=1):
            sheet.update_cell(i, 1, title)

        print("✅ Day titles updated")

    except Exception as e:
        print(f"🚨 Day title error: {e}")


update_day_titles(spreadsheet)

# -----------------------------
# IMAGE SETTINGS
# -----------------------------

x, y = 661, 356
url_prefix = "https://www.weather.gov/images/pbz/ghwo/"

# -----------------------------
# CATEGORY CONFIG
# -----------------------------

days_categories = {
    1: ["SevereThunderstorms","Tornado","ThunderstormWind","Hail","Lightning","ExcessiveRainfall","Wind","Fog","FireWeather","IceAccumulation","ExtremeHeat","SnowSleet","ExtremeCold","FrostFreeze"],
    2: ["SevereThunderstorms","Tornado","ThunderstormWind","Hail","Lightning","ExcessiveRainfall","Wind","Fog","FireWeather","IceAccumulation","ExtremeHeat","SnowSleet","ExtremeCold","FrostFreeze"],
    3: ["SevereThunderstorms","Lightning","ExcessiveRainfall","Wind","Fog","FireWeather","IceAccumulation","FrostFreeze","SnowSleet","ExtremeCold","ExtremeHeat"],
    4: ["Lightning","Wind","Fog","FireWeather","IceAccumulation","FrostFreeze","SnowSleet","ExtremeCold","ExtremeHeat","ExcessiveRainfall"],
    5: ["Lightning","Wind","FireWeather","IceAccumulation","FrostFreeze","ExtremeCold","ExtremeHeat","SnowSleet","ExcessiveRainfall"],
    6: ["Lightning","Wind","FireWeather","IceAccumulation","FrostFreeze","ExtremeCold","ExtremeHeat","SnowSleet"],
    7: ["Lightning","Wind","FireWeather","IceAccumulation","FrostFreeze","ExtremeCold","ExtremeHeat","SnowSleet"]
}

# -----------------------------
# COLOR CLASSIFICATION
# -----------------------------

COLOR_MAP = {
    "yellow": (255,255,0),
    "orange": (255,165,0),
    "red": (255,0,0),
    "pink": (255,0,255),
    "green": (0,255,0)
}

def color_distance(c1,c2):
    return math.sqrt(sum((a-b)**2 for a,b in zip(c1,c2)))

def is_grey(rgb,tolerance=20,brightness_threshold=160):
    r,g,b=rgb
    brightness=(r+g+b)/3
    return abs(r-g)<=tolerance and abs(g-b)<=tolerance and abs(r-b)<=tolerance and brightness<=brightness_threshold

def closest_color_name(rgb):
    distances={name:color_distance(rgb,target) for name,target in COLOR_MAP.items()}
    return min(distances,key=distances.get)

def classify_color(rgb,category):
    if is_grey(rgb):
        return "grey"

    best_match=closest_color_name(rgb)

    if best_match=="green":
        if category in ["SevereThunderstorms","Tornado","ThunderstormWind","Hail"]:
            return "green"
        return "grey"

    return best_match

# -----------------------------
# SHEET WRITER
# -----------------------------

def insert_data(sheet,new_data):
    if new_data:
        sheet.insert_rows(new_data,2)

# -----------------------------
# IMAGE PROCESSOR
# -----------------------------

def process_day(day_num,categories,sheet):

    current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    new_data=[]

    for category in categories:

        timestamp=int(time())
        image_url=f"{url_prefix}{category}Day{day_num}.jpg?cb={timestamp}"

        try:

            head=requests.head(image_url)
            last_modified=head.headers.get("Last-Modified","Not available")

            response=requests.get(image_url)

            if response.status_code==200:

                image=Image.open(BytesIO(response.content))

                if 0<=x<image.size[0] and 0<=y<image.size[1]:

                    rgb=image.getpixel((x,y))[:3]

                    color_name=classify_color(rgb,category)

                    rgb_str=f"{rgb[0]},{rgb[1]},{rgb[2]}"

                    new_data.append([
                        current_time,
                        last_modified,
                        f"Day {day_num}",
                        category,
                        color_name,
                        "",
                        "",
                        "",
                        rgb_str
                    ])

                    print(f"✅ {category} Day {day_num}: {rgb} → {color_name}")

            else:
                print(f"❌ {category} Day {day_num}: {response.status_code}")

        except Exception as e:
            print(f"🚨 {category} Day {day_num}: {e}")

    insert_data(sheet,new_data)

# -----------------------------
# LOAD WORKSHEETS
# -----------------------------

sheets={
1:spreadsheet.worksheet("Day1"),
2:spreadsheet.worksheet("Day2"),
3:spreadsheet.worksheet("Day3"),
4:spreadsheet.worksheet("Day4"),
5:spreadsheet.worksheet("Day5"),
6:spreadsheet.worksheet("Day6"),
7:spreadsheet.worksheet("Day7"),
}

# -----------------------------
# MAIN
# -----------------------------

for day_num,categories in days_categories.items():
    print(f"\nProcessing Day {day_num}")
    process_day(day_num,categories,sheets[day_num])

print("\n✅ Complete")
