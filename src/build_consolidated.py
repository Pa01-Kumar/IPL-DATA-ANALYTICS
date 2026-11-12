"""Combine per-match Cricsheet delivery CSV files into one raw table."""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def build_consolidated(raw_dir=None) -> Path:
    raw_dir = Path(raw_dir) if raw_dir is not None else ROOT / "data" / "raw"
    files = sorted(
        f for f in raw_dir.glob("*.csv")
        if not f.name.endswith("_info.csv") and f.name != "all_matches.csv"
    )
    if not files:
        raise FileNotFoundError(
            f"No per-match delivery CSV files found in {raw_dir}. "
            "Run 'python src/download_data.py' first."
        )

    frames = []
    for file_path in files:
        match_id = file_path.stem
        frame = pd.read_csv(file_path, dtype={"ball": str})
        if "match_id" in frame.columns:
            frame["match_id"] = match_id
        else:
            frame.insert(0, "match_id", match_id)
        frames.append(frame)

    all_matches = pd.concat(frames, ignore_index=True, sort=False)
    raw_dir.mkdir(parents=True, exist_ok=True)
    output = raw_dir / "all_matches.csv"
    all_matches.to_csv(output, index=False)
    print(f"Processed {len(files)} match files")
    print(f"Saved: {output.resolve()}")
    print(f"Rows: {len(all_matches)}")
    print(f"Columns: {all_matches.columns.tolist()}")
    return output


if __name__ == "__main__":
    build_consolidated()
