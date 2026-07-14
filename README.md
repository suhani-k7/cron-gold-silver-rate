# Gold and Silver Indian Rate Scraper (IST Timezone)

A Dockerized Python scraping application that fetches gold and silver rates for various cities in India from a multi-sheet Excel workbook (`urls_final.xlsx`) on an hourly cron schedule. All times and triggers operate in **Indian Standard Time (IST)**.

---

## Workspace Structure

```
.
├── Dockerfile              # Builds python-slim image with TZ=Asia/Kolkata and cron
├── README.md               # Detailed execution & setup instructions
├── crontab                 # Cron schedule configured for hourly runs (0 * * * *)
├── docker-compose.yml      # Service configurations with mounts for persistent data
├── entrypoint.sh           # startup script (exports env vars, runs scraper immediately, starts cron)
├── requirements.txt        # python dependencies
├── scraper.py              # Main scraping engine (BS4, multi-sheet reading, IST logic)
└── urls_final.xlsx         # Excel sheet containing URL targets and requested attributes
```

---

## Input File Structure (`urls_final.xlsx`)

The scraper reads from `urls_final.xlsx`, which contains three sheets:
1. **`Gold Rate`**:
   - Contains a column named `URLs` listing PolicyBazaar gold rate pages (e.g. `https://www.policybazaar.com/gold-rate/ahmedabad/`).
2. **`Silver Rate`**:
   - Contains a column named `URLs` listing PolicyBazaar silver rate pages (e.g. `https://www.policybazaar.com/silver-rate/ahmedabad/`).
3. **`attributes `**:
   - A list defining what data attributes are extracted and saved (24k, 22k, and 18k gold rates for 1gm, 8gm, 10gm, 12gm; silver rates; city names; and dates).

*Note: The city name is automatically extracted from the URL path (e.g., `ahmedabad` -> `Ahmedabad`).*

---

## Output Data Schema

All outputs are saved to the `./data` directory in IST:
- **`./data/rates.json`**: Active snapshot of the latest execution.
- **`./data/history.jsonl`**: Newline-delimited list of historical executions.

### Output JSON Format Example (Gold Entry)
```json
{
  "metal": "Gold",
  "city": "Ahmedabad",
  "url": "https://www.policybazaar.com/gold-rate/ahmedabad/",
  "fetched_at": "2026-07-14T10:50:32.739000+05:30",
  "error": null,
  "data": {
    "rate24k 1gm": 13864.0,
    "rate24k 8gm": 110912.0,
    "rate24k 10gm": 138640.0,
    "rate24k 12gm": 166368.0,
    "rate22k 1gm": 13204.0,
    "rate22k 8gm": 105632.0,
    "rate22k 10gm": 132040.0,
    "rate22k 12gm": 158448.0,
    "rate18k 1gm": null,
    "rate18k 8gm": null,
    "rate18k 10gm": null,
    "rate18k 12gm": null,
    "cityName": "Ahmedabad",
    "dayMonYear": "14 July 2026",
    "monYear": "July 2026",
    "currentYear": 2026
  }
}
```

---

## Detailed Execution Instructions

### Option 1: Run with Docker Compose (Recommended)

This is the preferred setup because it mounts the host directories. You can modify `urls_final.xlsx` on the host, and the container will automatically read the updated targets.

#### Step 1: Build and Launch the Container
Run the following command in the project directory:
```bash
docker compose up -d --build
```
*This command compiles the image, establishes the local `./data` directory, executes the scraping process once immediately (so you have initial files without waiting), and starts the cron scheduler in the background.*

#### Step 2: Verify Outputs on the Host
You will find the generated files inside `./data`:
```bash
# Check the snapshot rates file
cat data/rates.json

# Check the history tracking file
cat data/history.jsonl
```

#### Step 3: Monitor Live Container Logs
```bash
docker compose logs -f
```

#### Step 4: Stop the Container
```bash
docker compose down
```

---

### Option 2: Run with Raw Docker Commands
If you prefer not to use Docker Compose, you can build and run using docker CLI:

```bash
# 1. Build the image
docker build -t gold-silver-scraper .

# 2. Run the container, mounting local folders
docker run -d \
  --name gold-silver-scraper \
  -v "$(pwd)/data:/app/data" \
  -v "$(pwd)/urls_final.xlsx:/app/urls_final.xlsx" \
  --restart unless-stopped \
  gold-silver-scraper
```

---

### Option 3: Local Development (Without Docker)

You can run the script natively on your machine:

#### Step 1: Set up a Python Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
```

#### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

#### Step 3: Run the Scraper Script
```bash
python scraper.py
```
*The script will automatically detect it is running locally, read `./urls_final.xlsx` and write the JSON outputs to `./data/`.*

---

## How to Customize the Cron Trigger Schedule
By default, the scraper runs every hour on the hour (`0 * * * *`). To change this:
1. Open the [crontab](file:///Users/suhani/cron-gold-silver-rate/crontab) file.
2. Modify the schedule. For example, to run every 12 hours:
   ```cron
   0 */12 * * * /usr/local/bin/python /app/scraper.py >> /proc/1/fd/1 2>> /proc/1/fd/2
   ```
3. Rebuild and restart the container:
   ```bash
   docker compose up -d --build
   ```
