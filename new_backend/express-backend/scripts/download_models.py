#!/usr/bin/env python3
"""
Script to download required models for VoiceFlow.
Downloads Vosk speech recognition model and sentence transformer embedding model.
"""

import os
import urllib.request
import zipfile
import tarfile
import shutil
from pathlib import Path

def download_file(url, destination):
    """Download a file from URL to destination with progress"""
    print(f"Downloading {url} to {destination}")

    with urllib.request.urlopen(url) as response:
        total_size = int(response.headers.get('Content-Length', 0))
        downloaded = 0
        chunk_size = 8192

        with open(destination, 'wb') as f:
            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)

                if total_size > 0:
                    progress = (downloaded / total_size) * 100
                    print(".1f", end='', flush=True)

        print(" - Done!")

def extract_zip(zip_path, extract_to):
    """Extract zip file"""
    print(f"Extracting {zip_path} to {extract_to}")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    print("Extraction complete!")

def extract_tar_gz(tar_path, extract_to):
    """Extract tar.gz file"""
    print(f"Extracting {tar_path} to {extract_to}")
    with tarfile.open(tar_path, 'r:gz') as tar_ref:
        tar_ref.extractall(extract_to)
    print("Extraction complete!")

def download_vosk_model():
    """Download Vosk English model"""
    models_dir = Path("models")
    vosk_dir = models_dir / "vosk-model"
    vosk_dir.mkdir(parents=True, exist_ok=True)

    if vosk_dir.exists() and any(vosk_dir.iterdir()):
        print("Vosk model already exists, skipping download")
        return

    # Vosk English US model
    vosk_url = "https://alphacephei.com/vosk/models/vosk-model-en-us-0.22.zip"
    zip_path = models_dir / "vosk-model-en-us-0.22.zip"

    try:
        # Download
        download_file(vosk_url, zip_path)

        # Extract
        extract_zip(zip_path, models_dir)

        # Rename extracted folder
        extracted_dir = models_dir / "vosk-model-en-us-0.22"
        if extracted_dir.exists():
            extracted_dir.rename(vosk_dir)

        # Clean up zip file
        zip_path.unlink()

        print(f"Vosk model downloaded and extracted to {vosk_dir}")

    except Exception as e:
        print(f"Error downloading Vosk model: {e}")
        if zip_path.exists():
            zip_path.unlink()

def download_embedding_model():
    """Download sentence transformer embedding model"""
    models_dir = Path("models")
    embedding_dir = models_dir / "all-MiniLM-L6-v2"
    embedding_dir.mkdir(parents=True, exist_ok=True)

    if embedding_dir.exists() and any(embedding_dir.iterdir()):
        print("Embedding model already exists, skipping download")
        return

    # Sentence Transformers all-MiniLM-L6-v2 model
    embedding_url = "https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/resolve/main/model.tar.gz"
    tar_path = models_dir / "all-MiniLM-L6-v2.tar.gz"

    try:
        # Download
        download_file(embedding_url, tar_path)

        # Extract
        extract_tar_gz(tar_path, models_dir)

        # The model should be extracted to the correct directory
        # Clean up tar file
        tar_path.unlink()

        print(f"Embedding model downloaded and extracted to {embedding_dir}")

    except Exception as e:
        print(f"Error downloading embedding model: {e}")
        if tar_path.exists():
            tar_path.unlink()

def main():
    print("VoiceFlow Model Downloader")
    print("=" * 40)

    # Create models directory
    models_dir = Path("models")
    models_dir.mkdir(exist_ok=True)

    # Download models
    print("\n1. Downloading Vosk speech recognition model...")
    download_vosk_model()

    print("\n2. Downloading sentence transformer embedding model...")
    download_embedding_model()

    print("\n✅ All models downloaded successfully!")
    print("\nModel locations:")
    print(f"  - Vosk: models/vosk-model/")
    print(f"  - Embeddings: models/all-MiniLM-L6-v2/")

if __name__ == "__main__":
    main()