#!/usr/bin/env python3
"""
download_vosk_model.py

Download and extract a Vosk speech recognition model for the local Media Streams PoC.

Default behavior:
- downloads the small English Vosk model and extracts it to ../models/vosk-model

Usage:
  python download_vosk_model.py                # interactive, downloads default small English model
  python download_vosk_model.py --yes          # non-interactive, accept overwrite
  python download_vosk_model.py --url <URL>    # download a custom model zip URL

This script is intentionally dependency-free (uses standard library only).
"""
import argparse
import os
import sys
import urllib.request
import shutil
import zipfile
import tempfile

DEFAULT_MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DEST_ROOT = os.path.normpath(os.path.join(THIS_DIR, '..'))  # agent-workflow
DEFAULT_DEST = os.path.join(DEFAULT_DEST_ROOT, 'models', 'vosk-model')


def sizeof_fmt(num, suffix='B'):
    for unit in ['','K','M','G','T','P']:
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f}P{suffix}"


def download(url, out_path):
    print(f"Downloading model from: {url}")
    with urllib.request.urlopen(url) as resp:
        total = resp.getheader('Content-Length')
        if total:
            total = int(total)
            print(f"Total size: {sizeof_fmt(total)}")
        else:
            print("Total size: unknown")

        with open(out_path, 'wb') as out_file:
            shutil.copyfileobj(resp, out_file)


def extract_zip(zip_path, dest_dir):
    print(f"Extracting {zip_path} to {dest_dir}")
    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(dest_dir)


def find_extracted_topdir(dest_dir):
    # After extracting, try to detect a single top-level folder and return its path
    entries = [e for e in os.listdir(dest_dir) if not e.startswith('__MACOSX')]
    if len(entries) == 1:
        return os.path.join(dest_dir, entries[0])
    return None


def main():
    parser = argparse.ArgumentParser(description='Download and install a Vosk model into agent-workflow/models/vosk-model')
    parser.add_argument('--url', '-u', default=DEFAULT_MODEL_URL, help='URL to the Vosk model ZIP file')
    parser.add_argument('--dest', '-d', default=DEFAULT_DEST, help='Destination folder for the model (default: agent-workflow/models/vosk-model)')
    parser.add_argument('--yes', action='store_true', help='Accept prompts and overwrite existing model')

    args = parser.parse_args()
    url = args.url
    dest = os.path.abspath(args.dest)

    print(f"Destination model path: {dest}")

    if os.path.exists(dest) and not args.yes:
        print(f"A model already exists at {dest}")
        yn = input("Overwrite existing model? [y/N]: ")
        if yn.strip().lower() not in ('y', 'yes'):
            print("Aborting.")
            sys.exit(0)
        # remove existing
        print("Removing existing model folder...")
        shutil.rmtree(dest)

    os.makedirs(os.path.dirname(dest), exist_ok=True)

    with tempfile.TemporaryDirectory() as td:
        zip_path = os.path.join(td, 'model.zip')
        try:
            download(url, zip_path)
        except Exception as e:
            print(f"Download failed: {e}")
            sys.exit(2)

        extract_dir = os.path.join(td, 'extracted')
        os.makedirs(extract_dir, exist_ok=True)
        try:
            extract_zip(zip_path, extract_dir)
        except Exception as e:
            print(f"Failed to extract zip: {e}")
            sys.exit(3)

        top = find_extracted_topdir(extract_dir)
        if top:
            # Move the single top dir to the destination
            print(f"Found top-level directory in archive: {os.path.basename(top)}")
            shutil.move(top, dest)
        else:
            # If multiple files/dirs, create dest and move contents
            os.makedirs(dest, exist_ok=True)
            for entry in os.listdir(extract_dir):
                src = os.path.join(extract_dir, entry)
                dst = os.path.join(dest, entry)
                shutil.move(src, dst)

        print(f"Model installed at: {dest}")
        print("Done.")


if __name__ == '__main__':
    main()
