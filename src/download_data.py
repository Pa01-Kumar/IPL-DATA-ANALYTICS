import requests
import zipfile
import io
from pathlib import Path

# Where to save the files
raw_dir = Path("data/raw")
raw_dir.mkdir(parents=True, exist_ok=True)

# Official Cricsheet IPL CSV archive
url = "https://cricsheet.org/downloads/ipl_csv2.zip"

print("Downloading from Cricsheet...")
response = requests.get(url)
response.raise_for_status()   # stops with an error if the download failed

print("Downloaded. Unzipping...")
with zipfile.ZipFile(io.BytesIO(response.content)) as z:
    z.extractall(raw_dir)

print("Done. Files are in:", raw_dir.resolve())