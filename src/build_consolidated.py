from pathlib import Path
import pandas as pd

raw_dir = Path("data/raw")

# All per-match delivery files (skip metadata + skip any previous output)
files = sorted(
    f for f in raw_dir.glob("*.csv")
    if not f.name.endswith("_info.csv") and f.name != "all_matches.csv"
)
print(f"Found {len(files)} match delivery files")

frames = []
for f in files:
    match_id = f.stem
    df = pd.read_csv(f, dtype={"ball": str})
    if "match_id" in df.columns:
        df["match_id"] = match_id          # overwrite to keep type consistent
    else:
        df.insert(0, "match_id", match_id) # only add if missing
    frames.append(df)

all_matches = pd.concat(frames, ignore_index=True, sort=False)

out_path = raw_dir / "all_matches.csv"
all_matches.to_csv(out_path, index=False)

print("Saved:", out_path.resolve())
print("Rows:", len(all_matches))
print("Columns:", all_matches.columns.tolist())