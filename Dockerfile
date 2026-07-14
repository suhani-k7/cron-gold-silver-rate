FROM python:3.11-slim

# Set environment variable for Timezone
ENV TZ=Asia/Kolkata

# Install system dependencies: cron, procps, and tzdata (for timezone support)
RUN apt-get update && apt-get install -y \
    cron \
    procps \
    tzdata \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy and install python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY scraper.py /app/
COPY entrypoint.sh /app/
COPY crontab /app/

# Setup permissions for the entrypoint script
RUN chmod +x /app/entrypoint.sh

# Configure cron job
RUN cp /app/crontab /etc/cron.d/scraper-cron \
    && chmod 0644 /etc/cron.d/scraper-cron \
    

# Create the data output directory inside the container
RUN mkdir -p /app/data

# Define the entrypoint script to run on start
ENTRYPOINT ["/app/entrypoint.sh"]
