import sys
import trafilatura
import requests
import json

url = sys.argv[1]
try:
  response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
  response.raise_for_status()
  html = response.text
  text = trafilatura.extract(html, include_comments=False, include_tables=True)
  if not text:
    raise ValueError('No content extracted')
  print(json.dumps({"text": text, "url": url}))
except Exception as e:
  print(json.dumps({"error": str(e), "url": url}))