import requests
from PIL import Image
from io import BytesIO
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import math
from time import time
import os

# --- Selenium & BeautifulSoup for day titles ---
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

# --- Toggle image saving ---
SAVE_IMAGES = False  # Set to False to disable saving
IMAGE_SAVE_BASE = "/Users/kyleolmstead/Desktop/EHWO/Images"
timestamp_str = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
IMAGE_SAVE_FOLDER = os.path.join(IMAGE_SAVE_BASE, timestamp_str)
if SAVE_IMAGES:
    os.makedirs(IMAGE_SAVE_FOLDER, exist_ok=True)

# --- Google Sheets setup ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name("/Users/kyleolmstead/Desktop/EHWO/credentials.json", scope)
client = gspread.authorize(credentials)
workbook_id = "1iO4dA5NEP1sKYTEFn6m38-f1m1K7H2CScTfzEXb_KbA"
spreadsheet = client.open_by_key(workbook_id)

# --- Selenium-based day titles updater ---
def update_day_titles(spreadsheet):
    try:
        options = Options()
        #options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")

        service = Service("/opt/homebrew/bin/chromedriver")  # correct path
        driver = webdriver.Chrome(service=service, options=options)
        driver.get("https://www.weather.gov/pbz/ehwo")

        # Wait up to 15 seconds for all day <th> elements after the first (dropdown)
        day_th_elements = WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located(
                (By.XPATH, '//tr[@id="riskTitleRow"]/th[position()>1]')
            )
        )

        # Grab their text dynamically
        day_titles = [th.text.strip() for th in day_th_elements]
        driver.quit()

        if not day_titles:
            print("⚠️ Day titles not found after render.")
            return

        print("📅 Day titles:", day_titles)

        # Write to "Day_Names" sheet A1-A7
        sheet = spreadsheet.worksheet("Day_Names")
        for i, title in enumerate(day_titles, start=1):
            sheet.update_cell(i, 1, title)

        print("✅ Day titles updated in 'Day_Names'.")
    except Exception as e:
        print(f"🚨 Error updating day titles: {e}")

# --- Update day titles first ---
update_day_titles(spreadsheet)

# --- Image settings ---
x, y = 661, 356
url_prefix = "https://www.weather.gov/images/pbz/ghwo/"

# --- Categories per day ---
days_categories = {
    1: ["SevereThunderstorms", "Tornado", "ThunderstormWind", "Hail", "Lightning", "ExcessiveRainfall", "Wind", "Fog", "FireWeather", "IceAccumulation", "ExtremeHeat", "SnowSleet", "ExtremeCold", "FrostFreeze"],
    2: ["SevereThunderstorms", "Tornado", "ThunderstormWind", "Hail", "Lightning", "ExcessiveRainfall", "Wind", "Fog", "FireWeather", "IceAccumulation", "ExtremeHeat", "SnowSleet", "ExtremeCold", "FrostFreeze"],
    3: ["SevereThunderstorms", "Lightning", "ExcessiveRainfall", "Wind", "Fog", "FireWeather", "IceAccumulation", "FrostFreeze", "SnowSleet", "ExtremeCold", "ExtremeHeat"],
    4: ["Lightning", "Wind", "Fog", "FireWeather", "IceAccumulation", "FrostFreeze", "SnowSleet", "ExtremeCold", "ExtremeHeat", "ExcessiveRainfall"],
    5: ["Lightning", "Wind", "FireWeather", "IceAccumulation", "FrostFreeze", "ExtremeCold", "ExtremeHeat", "SnowSleet", "ExcessiveRainfall"],
    6: ["Lightning", "Wind", "FireWeather", "IceAccumulation", "FrostFreeze", "ExtremeCold", "ExtremeHeat", "SnowSleet"],
    7: ["Lightning", "Wind", "FireWeather", "IceAccumulation", "FrostFreeze", "ExtremeCold", "ExtremeHeat", "SnowSleet"]
}

# --- Color classification setup ---
COLOR_MAP = {
    "yellow": (255, 255, 0),
    "orange": (255, 165, 0),
    "red": (255, 0, 0),
    "pink": (255, 0, 255),
    "green": (0, 255, 0),
}

def color_distance(c1, c2):
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(c1, c2)))

def is_grey(rgb, tolerance=20, brightness_threshold=160):
    r, g, b = rgb
    brightness = (r + g + b) / 3
    return (
        abs(r - g) <= tolerance and
        abs(g - b) <= tolerance and
        abs(r - b) <= tolerance and
        brightness <= brightness_threshold
    )

def closest_color_name(rgb):
    distances = {name: color_distance(rgb, target) for name, target in COLOR_MAP.items()}
    return min(distances, key=distances.get)

def classify_color(rgb, category):
    if is_grey(rgb):
        return "grey"
    best_match = closest_color_name(rgb)
    if best_match == "green":
        return "green" if category in ["SevereThunderstorms", "Tornado", "ThunderstormWind", "Hail"] else "grey"
    return best_match

# --- Sheet writer ---
def insert_data(sheet, new_data):
    if new_data:
        sheet.insert_rows(new_data, 2)

# --- Image processor ---
def process_day(day_num, categories, sheet):
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    new_data = []

    for category in categories:
        timestamp = int(time())
        image_url_base = f"{url_prefix}{category}Day{day_num}.jpg"
        image_url = f"{image_url_base}?cb={timestamp}"

        try:
            head_response = requests.head(image_url)
            last_modified = head_response.headers.get("Last-Modified", "Not available") if head_response.status_code == 200 else "Not available"
            
            response = requests.get(image_url)
            if response.status_code == 200:
                image = Image.open(BytesIO(response.content))

                if SAVE_IMAGES:
                    filename = f"Day{day_num}_{category}.jpg"
                    image.save(os.path.join(IMAGE_SAVE_FOLDER, filename))

                if 0 <= x < image.size[0] and 0 <= y < image.size[1]:
                    rgb_color = image.getpixel((x, y))
                    rgb_only = rgb_color[:3] if len(rgb_color) >= 3 else rgb_color
                    color_name = classify_color(rgb_only, category)
                    rgb_str = f"{rgb_only[0]},{rgb_only[1]},{rgb_only[2]}"
                    
                    new_data.append([current_time, last_modified, f"Day {day_num}", category, color_name, '', '', '', rgb_str])
                    print(f"✅ {category} Day {day_num}: RGB={rgb_only} → {color_name}")
                else:
                    print(f"⚠️ {category} Day {day_num}: Pixel ({x},{y}) out of bounds")
            else:
                print(f"❌ {category} Day {day_num}: Failed to download image ({response.status_code})")
        
        except Exception as e:
            print(f"🚨 {category} Day {day_num}: Error → {e}")
    
    insert_data(sheet, new_data)

# --- Load worksheets ---
sheets = {
    1: spreadsheet.worksheet("Day1"),
    2: spreadsheet.worksheet("Day2"),
    3: spreadsheet.worksheet("Day3"),
    4: spreadsheet.worksheet("Day4"),
    5: spreadsheet.worksheet("Day5"),
    6: spreadsheet.worksheet("Day6"),
    7: spreadsheet.worksheet("Day7"),
}

# --- Main execution ---
for day_num, categories in days_categories.items():
    print(f"\n🔄 Processing Day {day_num}...")
    process_day(day_num, categories, sheets[day_num])

print("\n✅ All data sent to Google Sheets.")

# --- Webhook trigger (optional) ---
script_url = "https://script.google.com/macros/s/AKfycbxTH3ktjD2EU5LvQ1QRj1KuixJya-sWyfkA11h9IfI4Udae46V2D8Zv0ef8KWQNvJzkBw/exec"
try:
    response = requests.get(script_url)
    if response.status_code == 200:
        print("📡 Webhook triggered successfully.")
    else:
        print(f"⚠️ Webhook failed: {response.status_code}")
except Exception as e:
    print(f"🚨 Webhook error: {e}")