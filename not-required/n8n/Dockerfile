FROM docker.n8n.io/n8nio/n8n:latest

USER root

# Install system dependencies for Bun, Puppeteer (Chromium), and Python (Trafilatura)
RUN apk update && apk add --no-cache \
    python3 \
    py3-pip \
    chromium \
    libstdc++ \
    gcompat \
    libgcc \
    libx11 \
    libxcomposite \
    libxdamage \
    libxext \
    libxrandr \
    alsa-lib \
    curl \
    bash \
    unzip \
    && rm -rf /var/cache/apk/*

# Install Bun
RUN curl -fsSL https://bun.sh/install | bash
RUN chmod +x /root/.bun/bin/bun
ENV PATH="/root/.bun/bin:$PATH"

# Verify Bun installation works as root
RUN bun -v

# Install Puppeteer using Bun
RUN bun install -g puppeteer

# Install Trafilatura for text extraction (no need for torch/sentence-transformers since we use Ollama)
RUN pip3 install --no-cache-dir --break-system-packages trafilatura requests

# Set environment variables for Puppeteer
ENV PUPPETEER_EXECUTABLE_PATH="/usr/bin/chromium-browser"

# Create directories and set permissions for node user
RUN mkdir -p /home/node/.cache && chown -R node:node /home/node
RUN mkdir -p /app/scripts && chown -R node:node /app
RUN chmod -R 755 /app/scripts

# Make bun accessible to node user by copying it to a public location
RUN cp /root/.bun/bin/bun /usr/local/bin/bun && chmod +x /usr/local/bin/bun

# Create file-based scrape command for unlimited data handling
RUN echo '#!/bin/bash' > /usr/local/bin/scrape && \
    echo '# Fix permissions on scripts directory' >> /usr/local/bin/scrape && \
    echo 'if [ -d "/app/scripts" ]; then' >> /usr/local/bin/scrape && \
    echo '  chown -R node:node /app/scripts 2>/dev/null || true' >> /usr/local/bin/scrape && \
    echo '  chmod -R 755 /app/scripts 2>/dev/null || true' >> /usr/local/bin/scrape && \
    echo 'fi' >> /usr/local/bin/scrape && \
    echo '' >> /usr/local/bin/scrape && \
    echo '# Create output directory for scraped data' >> /usr/local/bin/scrape && \
    echo 'mkdir -p /tmp/scraped_data' >> /usr/local/bin/scrape && \
    echo '' >> /usr/local/bin/scrape && \
    echo '# Generate unique filename with timestamp' >> /usr/local/bin/scrape && \
    echo 'TIMESTAMP=$(date +%s)' >> /usr/local/bin/scrape && \
    echo 'OUTPUT_FILE="/tmp/scraped_data/scraped_${TIMESTAMP}_$$.json"' >> /usr/local/bin/scrape && \
    echo '' >> /usr/local/bin/scrape && \
    echo '# Try static scraper first, then fallback to Puppeteer' >> /usr/local/bin/scrape && \
    echo 'if python3 /app/scripts/static_scraper.py "$1" > "$OUTPUT_FILE" 2>/dev/null; then' >> /usr/local/bin/scrape && \
    echo '  SCRAPER_USED="static"' >> /usr/local/bin/scrape && \
    echo 'elif bun /app/scripts/scraper.js "$1" > "$OUTPUT_FILE" 2>/dev/null; then' >> /usr/local/bin/scrape && \
    echo '  SCRAPER_USED="puppeteer"' >> /usr/local/bin/scrape && \
    echo 'else' >> /usr/local/bin/scrape && \
    echo '  echo "{\"error\": \"Both scraping methods failed\", \"url\": \"$1\"}"' >> /usr/local/bin/scrape && \
    echo '  exit 1' >> /usr/local/bin/scrape && \
    echo 'fi' >> /usr/local/bin/scrape && \
    echo '' >> /usr/local/bin/scrape && \
    echo '# Get file size and return metadata with file path' >> /usr/local/bin/scrape && \
    echo 'FILE_SIZE=$(stat -c%s "$OUTPUT_FILE" 2>/dev/null || echo "0")' >> /usr/local/bin/scrape && \
    echo 'echo "{\"file_path\": \"$OUTPUT_FILE\", \"url\": \"$1\", \"size_bytes\": $FILE_SIZE, \"scraper_used\": \"$SCRAPER_USED\", \"timestamp\": $TIMESTAMP}"' >> /usr/local/bin/scrape && \
    chmod +x /usr/local/bin/scrape

# Create read-scraped-data command to retrieve file contents
RUN echo '#!/bin/bash' > /usr/local/bin/read-scraped-data && \
    echo 'if [ -z "$1" ]; then' >> /usr/local/bin/read-scraped-data && \
    echo '  echo "{\"error\": \"File path required\"}"' >> /usr/local/bin/read-scraped-data && \
    echo '  exit 1' >> /usr/local/bin/read-scraped-data && \
    echo 'fi' >> /usr/local/bin/read-scraped-data && \
    echo 'if [ -f "$1" ]; then' >> /usr/local/bin/read-scraped-data && \
    echo '  cat "$1"' >> /usr/local/bin/read-scraped-data && \
    echo 'else' >> /usr/local/bin/read-scraped-data && \
    echo '  echo "{\"error\": \"File not found: $1\"}"' >> /usr/local/bin/read-scraped-data && \
    echo '  exit 1' >> /usr/local/bin/read-scraped-data && \
    echo 'fi' >> /usr/local/bin/read-scraped-data && \
    chmod +x /usr/local/bin/read-scraped-data

# Install sudo and allow node user to fix permissions without password
RUN apk add --no-cache sudo && \
    echo 'node ALL=(ALL) NOPASSWD: /bin/chown, /bin/chmod' >> /etc/sudoers

USER node

# Verify Bun, Puppeteer, and Trafilatura
RUN bun -v && \
    bun -e "require('puppeteer'); console.log('Puppeteer installed')" && \
    python3 -c "import trafilatura; print('Trafilatura installed')"