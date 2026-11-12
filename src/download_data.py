"""Download and safely extract the official Cricsheet IPL CSV archive."""
from __future__ import annotations

from io import BytesIO
from pathlib import Path, PurePosixPath
import stat
import zipfile

URL = "https://cricsheet.org/downloads/ipl_csv2.zip"
ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"


def safe_extract_zip(content: bytes, destination: Path) -> int:
    """Extract a ZIP only after rejecting traversal, absolute paths and symlinks."""
    stream = BytesIO(content)
    if not zipfile.is_zipfile(stream):
        raise ValueError("Cricsheet response is not a valid ZIP archive.")
    stream.seek(0)
    destination = Path(destination).resolve()
    destination.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(stream) as archive:
        for info in archive.infolist():
            member = PurePosixPath(info.filename)
            mode = info.external_attr >> 16
            if "\\" in info.filename or member.is_absolute() or ".." in member.parts:
                raise ValueError(f"Unsafe archive member path: {info.filename}")
            if member.parts and ":" in member.parts[0]:
                raise ValueError(f"Unsafe archive member path: {info.filename}")
            if stat.S_ISLNK(mode):
                raise ValueError(f"Symbolic links are not allowed: {info.filename}")
            target = (destination / Path(*member.parts)).resolve()
            if target != destination and destination not in target.parents:
                raise ValueError(f"Archive member escapes destination: {info.filename}")
        archive.extractall(destination)
        return len(archive.infolist())


def main() -> None:
    import requests

    print("Downloading official Cricsheet IPL CSV archive...")
    response = requests.get(URL, timeout=(10, 120))
    response.raise_for_status()
    count = safe_extract_zip(response.content, RAW_DIR)
    print(f"Extracted {count} archive entries into {RAW_DIR}")


if __name__ == "__main__":
    main()
