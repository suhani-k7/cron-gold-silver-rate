FROM python:3.11-slim

# Set environment variable for Timezone (harmless to keep even though
# scraper.py computes IST via a fixed UTC+5:30 offset internally;
# this keeps container-level tooling/logs consistent with IST too).
ENV TZ=Asia/Kolkata
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Set working directory
WORKDIR /app

# Copy and install python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY scraper.py /app/
COPY urls_final.xlsx /app/

# scraper.py's own main() loop handles hourly scheduling (sleeps until the
# next hour, forever) when RUN_HOURLY is unset/true — no cron needed.
# For one-shot CI runs, override with -e RUN_HOURLY=false.
CMD ["python", "scraper.py"]