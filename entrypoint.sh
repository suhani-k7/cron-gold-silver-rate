#!/bin/bash
set -e

# Export environment variables so the cron job execution context can access them.
# The cron daemon runs in a clean environment, so loading /etc/environment ensures Python paths
# and any custom configurations or proxies are correctly resolved.
env | grep -v 'no_proxy' > /etc/environment

# Run the scraper once immediately on container startup.
# This ensures that output data is immediately available without waiting for the first cron tick.
echo "=== Running Initial Scrape ==="
python /app/scraper.py

# Start the cron daemon in the foreground (PID 1)
echo "=== Starting Cron Daemon ==="
exec cron -f
