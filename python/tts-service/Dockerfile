FROM python:3.11-slim

WORKDIR /app

# System deps for audio processing (pydub needs ffmpeg)
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY main.py .

# Create presets directory (mount or bake in reference WAVs here)
RUN mkdir -p /app/presets

EXPOSE 8060

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8060"]
