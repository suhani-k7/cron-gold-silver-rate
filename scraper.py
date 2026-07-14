import os
import re
import json
import logging
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import requests
from bs4 import BeautifulSoup

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)

# Timezone Configuration: Indian Standard Time (IST)
IST_TZ = timezone(timedelta(hours=5, minutes=30))

# Paths Configuration
EXCEL_PATH = "/app/urls_final.xlsx" if os.path.exists("/app/urls_final.xlsx") else "./urls_final.xlsx"
DATA_DIR = "/app/data" if os.path.exists("/app") else "./data"

# Separate output files for gold and silver
GOLD_JSON_PATH = os.path.join(DATA_DIR, "gold_rates.json")
SILVER_JSON_PATH = os.path.join(DATA_DIR, "silver_rates.json")
HISTORY_JSONL_PATH = os.path.join(DATA_DIR, "history.jsonl")

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

def clean_and_parse_rate(text):
    """
    Cleans raw text (extracts digit patterns, handles commas/periods)
    and returns a float rate value.
    """
    if not text:
        return None

    # Remove whitespace and common currency symbols
    cleaned = re.sub(r'[^\d.,]', '', text).strip()

    if not cleaned:
        return None

    # Check for cases with both thousands and decimals e.g., 2,350.50
    if ',' in cleaned and '.' in cleaned:
        cleaned = cleaned.replace(',', '')
    # Check for cases with only commas, e.g., 2350,50 (European format) or 2,350 (thousands)
    elif ',' in cleaned and '.' not in cleaned:
        parts = cleaned.split(',')
        if len(parts[-1]) == 3:
            # Likely a thousands separator (e.g. 2,350)
            cleaned = cleaned.replace(',', '')
        else:
            # Likely a decimal comma (e.g. 51,77)
            cleaned = cleaned.replace(',', '.')

    # Extract the first float-like substring
    match = re.search(r'\d+(?:\.\d+)?', cleaned)
    if match:
        return float(match.group(0))
    return None

def parse_date_details(title_text, ist_now):
    """
    Extracts date information from the page title, e.g., "(14 July 2026)"
    and returns (dayMonYear, monYear, currentYear).
    """
    # Default values based on the current IST time
    dayMonYear = ist_now.strftime("%d %B %Y").lstrip("0")
    monYear = ist_now.strftime("%B %Y")
    currentYear = ist_now.year

    if not title_text:
        return dayMonYear, monYear, currentYear

    # Search for something in parentheses like (14 July 2026)
    match = re.search(r'\(([^)]+)\)', title_text)
    if match:
        extracted = match.group(1).strip()
        parts = extracted.split()
        if len(parts) >= 3:
            dayMonYear = extracted
            monYear = " ".join(parts[1:])
            # Try to convert year to integer, fallback to string if fails
            try:
                currentYear = int(parts[-1])
            except ValueError:
                currentYear = parts[-1]

    return dayMonYear, monYear, currentYear

def scrape_gold_page(url, ist_now):
    """
    Scrapes a PolicyBazaar Gold Rate page.
    """
    headers = {"User-Agent": USER_AGENT}
    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()

    soup = BeautifulSoup(response.content, "lxml")

    # 1. Parse City Name from URL
    city_name = url.rstrip('/').split('/')[-1].replace('-', ' ').title()

    # 2. Parse Date Details from Title
    title_text = soup.title.string if soup.title else ""
    dayMonYear, monYear, currentYear = parse_date_details(title_text, ist_now)

    # 3. Locate Gold Tables
    # We find all tables containing gram rows (e.g., "1 Gram", "10 Gram")
    gold_rate_tables = []
    for table in soup.find_all('table'):
        has_gram_rows = False
        for tr in table.find_all('tr'):
            cells = [td.get_text(strip=True) for td in tr.find_all(['td', 'th'])]
            if cells and any("1 Gram" in c or "10 Gram" in c or "12 Gram" in c for c in cells):
                has_gram_rows = True
                break
        if has_gram_rows:
            gold_rate_tables.append(table)

    # Helper function to parse a gold rate table grid
    def parse_table_grid(table):
        grid = {}
        for tr in table.find_all('tr'):
            cells = [td.get_text(strip=True) for td in tr.find_all(['td', 'th'])]
            if len(cells) >= 2:
                label = cells[0].lower().strip()
                val = clean_and_parse_rate(cells[1])
                # Check for precise label matching
                if "1 gram" in label and "8 gram" not in label and "10 gram" not in label and "12 gram" not in label:
                    grid["1gm"] = val
                elif "8 gram" in label:
                    grid["8gm"] = val
                elif "10 gram" in label:
                    grid["10gm"] = val
                elif "12 gram" in label:
                    grid["12gm"] = val
        return grid

    # Extract 24k and 22k data if tables exist
    data_24k = parse_table_grid(gold_rate_tables[0]) if len(gold_rate_tables) > 0 else {}
    data_22k = parse_table_grid(gold_rate_tables[1]) if len(gold_rate_tables) > 1 else {}

    # Assemble properties matching the attributes sheet requirements
    attributes = {
        "rate24k 1gm": data_24k.get("1gm"),
        "rate24k 8gm": data_24k.get("8gm"),
        "rate24k 10gm": data_24k.get("10gm"),
        "rate24k 12gm": data_24k.get("12gm"),
        "rate22k 1gm": data_22k.get("1gm"),
        "rate22k 8gm": data_22k.get("8gm"),
        "rate22k 10gm": data_22k.get("10gm"),
        "rate22k 12gm": data_22k.get("12gm"),
        "rate18k 1gm": None,
        "rate18k 8gm": None,
        "rate18k 10gm": None,
        "rate18k 12gm": None,
        "cityName": city_name,
        "dayMonYear": dayMonYear,
        "monYear": monYear,
        "currentYear": currentYear
    }

    return attributes

def scrape_silver_page(url, ist_now):
    """
    Scrapes a PolicyBazaar Silver Rate page.
    """
    headers = {"User-Agent": USER_AGENT}
    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()

    soup = BeautifulSoup(response.content, "lxml")

    # 1. Parse City Name from URL
    city_name = url.rstrip('/').split('/')[-1].replace('-', ' ').title()

    # 2. Parse Date Details from Title
    title_text = soup.title.string if soup.title else ""
    dayMonYear, monYear, currentYear = parse_date_details(title_text, ist_now)

    # 3. Locate Silver Table containing gram columns
    data_silver = {}
    for table in soup.find_all('table'):
        # Check if this table has rows like "1gm", "8gm"
        is_silver_table = False
        temp_data = {}
        for tr in table.find_all('tr'):
            cells = [td.get_text(strip=True) for td in tr.find_all(['td', 'th'])]
            if len(cells) >= 2:
                label = cells[0].lower().strip()
                val = clean_and_parse_rate(cells[1])
                if label in ["1gm", "8gm", "10gm", "100gm", "1000gm", "1kg"]:
                    is_silver_table = True
                    target_label = "1000gm" if label in ["1000gm", "1kg"] else label
                    temp_data[target_label] = val
        if is_silver_table:
            data_silver = temp_data
            break

    # Assemble properties matching silver requirements
    attributes = {
        "rate 1gm": data_silver.get("1gm"),
        "rate 8gm": data_silver.get("8gm"),
        "rate 10gm": data_silver.get("10gm"),
        "rate 100gm": data_silver.get("100gm"),
        "rate 1000gm": data_silver.get("1000gm"),
        "cityName": city_name,
        "dayMonYear": dayMonYear,
        "monYear": monYear,
        "currentYear": currentYear
    }

    return attributes

def scrape_item(metal, url):
    """
    General entry scraping handler converting timing to IST.
    """
    ist_now = datetime.now(IST_TZ)
    fetched_at = ist_now.isoformat()
    city_name = url.rstrip('/').split('/')[-1].replace('-', ' ').title()

    logging.info(f"Starting scrape for {metal} in {city_name} via {url}")

    try:
        if metal.lower() == "gold":
            attributes = scrape_gold_page(url, ist_now)
        else:
            attributes = scrape_silver_page(url, ist_now)

        logging.info(f"Successfully scraped {metal} for {city_name}")
        return attributes, None, fetched_at
    except Exception as e:
        error_msg = str(e)
        logging.error(f"Error scraping {metal} for {city_name}: {error_msg}")
        return None, error_msg, fetched_at

def main():
    if not os.path.exists(EXCEL_PATH):
        logging.critical(f"Input Excel file not found at: {EXCEL_PATH}")
        return

    # Ensure output data directory exists
    os.makedirs(DATA_DIR, exist_ok=True)

    try:
        xl = pd.ExcelFile(EXCEL_PATH)
        gold_df = pd.read_excel(xl, sheet_name="Gold Rate") if "Gold Rate" in xl.sheet_names else pd.DataFrame(columns=["URLs"])
        silver_df = pd.read_excel(xl, sheet_name="Silver Rate") if "Silver Rate" in xl.sheet_names else pd.DataFrame(columns=["URLs"])
    except Exception as e:
        logging.critical(f"Failed to read Excel file {EXCEL_PATH}: {str(e)}")
        return

    gold_rates = []
    silver_rates = []
    generated_at = datetime.now(IST_TZ).isoformat()

    # We use a ThreadPoolExecutor with 10 workers for concurrent scraping
    # This prevents blocking of the scraping process while maintaining safety against excessive rate limiting.
    with ThreadPoolExecutor(max_workers=10) as executor:
        # Submit Gold tasks
        gold_tasks = []
        if "URLs" in gold_df.columns:
            for url in gold_df["URLs"].dropna():
                url_str = str(url).strip()
                if url_str:
                    future = executor.submit(scrape_item, "Gold", url_str)
                    gold_tasks.append((url_str, future))

        # Submit Silver tasks
        silver_tasks = []
        if "URLs" in silver_df.columns:
            for url in silver_df["URLs"].dropna():
                url_str = str(url).strip()
                if url_str:
                    future = executor.submit(scrape_item, "Silver", url_str)
                    silver_tasks.append((url_str, future))

        # Gather Gold results in the original row order
        for url_str, future in gold_tasks:
            city_name = url_str.rstrip('/').split('/')[-1].replace('-', ' ').title()
            try:
                data, error, fetched_at = future.result()
                gold_rates.append({
                    "metal": "Gold",
                    "city": city_name,
                    "url": url_str,
                    "fetched_at": fetched_at,
                    "error": error,
                    "data": data
                })
            except Exception as e:
                gold_rates.append({
                    "metal": "Gold",
                    "city": city_name,
                    "url": url_str,
                    "fetched_at": datetime.now(IST_TZ).isoformat(),
                    "error": f"Execution error: {str(e)}",
                    "data": None
                })

        # Gather Silver results in the original row order
        for url_str, future in silver_tasks:
            city_name = url_str.rstrip('/').split('/')[-1].replace('-', ' ').title()
            try:
                data, error, fetched_at = future.result()
                silver_rates.append({
                    "metal": "Silver",
                    "city": city_name,
                    "url": url_str,
                    "fetched_at": fetched_at,
                    "error": error,
                    "data": data
                })
            except Exception as e:
                silver_rates.append({
                    "metal": "Silver",
                    "city": city_name,
                    "url": url_str,
                    "fetched_at": datetime.now(IST_TZ).isoformat(),
                    "error": f"Execution error: {str(e)}",
                    "data": None
                })

    # Prepare current run snapshots (one per metal)
    gold_snapshot = {
        "generated_at": generated_at,
        "rates": gold_rates
    }
    silver_snapshot = {
        "generated_at": generated_at,
        "rates": silver_rates
    }

    # Write gold snapshot (overwritten)
    try:
        with open(GOLD_JSON_PATH, "w") as f:
            json.dump(gold_snapshot, f, indent=2)
        logging.info(f"Saved gold snapshot to {GOLD_JSON_PATH}")
    except Exception as e:
        logging.error(f"Failed to write gold_rates.json: {str(e)}")

    # Write silver snapshot (overwritten)
    try:
        with open(SILVER_JSON_PATH, "w") as f:
            json.dump(silver_snapshot, f, indent=2)
        logging.info(f"Saved silver snapshot to {SILVER_JSON_PATH}")
    except Exception as e:
        logging.error(f"Failed to write silver_rates.json: {str(e)}")

    # Compile lightweight history entry with timestamp and errors only
    all_rates = gold_rates + silver_rates
    errors = []
    for r in all_rates:
        if r.get("error"):
            errors.append({
                "metal": r["metal"],
                "city": r["city"],
                "url": r["url"],
                "error": r["error"]
            })

    history_entry = {
        "generated_at": generated_at,
        "total_urls": len(all_rates),
        "successful_urls": len(all_rates) - len(errors),
        "failed_urls": len(errors),
        "errors": errors
    }

    # Write to history (appended as JSONL)
    try:
        with open(HISTORY_JSONL_PATH, "a") as f:
            f.write(json.dumps(history_entry) + "\n")
        logging.info(f"Appended entry to {HISTORY_JSONL_PATH}")
    except Exception as e:
        logging.error(f"Failed to append to history.jsonl: {str(e)}")

if __name__ == "__main__":
    main()