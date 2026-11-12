"""Prepare a normalized IPL auction transaction file from a source CSV.

This utility deliberately creates an UNVERIFIED provenance manifest. Review the
source terms, price currency/unit, coverage and sold/unsold semantics manually
before changing verified to true.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

COLUMN_ALIASES = {
    "player": ("player", "player name", "players list", "player's list"),
    "auction_year": ("auction_year", "auction year", "year"),
    "sold_price": ("sold_price", "sold price", "sold price (inr)", "cost in ₹ (cr.)"),
    "role": ("role", "playing role", "type"),
}
PRICE_TO_LAKH = {
    "inr": 1 / 100_000,
    "inr-lakh": 1.0,
    "inr-crore": 100.0,
}


def _find_column(columns, aliases):
    normalized = {str(c).strip().lower(): c for c in columns}
    for alias in aliases:
        if alias in normalized:
            return normalized[alias]
    return None


def prepare_auction_csv(
    source: Path,
    output: Path,
    *,
    source_name: str,
    source_url: str,
    price_unit: str,
    accessed_on: str,
) -> tuple[int, Path]:
    raw = pd.read_csv(source)
    selected = {
        key: _find_column(raw.columns, aliases)
        for key, aliases in COLUMN_ALIASES.items()
    }
    missing = [key for key in ("player", "auction_year", "sold_price")
               if selected[key] is None]
    if missing:
        raise ValueError("Source CSV is missing required fields: " + ", ".join(missing))

    data = pd.DataFrame({
        "player": raw[selected["player"]].astype("string").str.strip(),
        "auction_year": pd.to_numeric(raw[selected["auction_year"]], errors="coerce"),
        "sold_price_lakh": pd.to_numeric(
            raw[selected["sold_price"]].astype("string").str.replace(",", "", regex=False)
            .str.replace(r"[^0-9.\-]", "", regex=True), errors="coerce"
        ) * PRICE_TO_LAKH[price_unit],
    })
    # Retained only as a pre-auction categorical attribute; franchise/team and
    # all other source columns are intentionally discarded.
    if selected["role"] is not None:
        data["role"] = raw[selected["role"]].astype("string").str.strip()

    data = data.dropna(subset=["player", "auction_year", "sold_price_lakh"])
    data = data[data["player"].ne("") & data["sold_price_lakh"].gt(0)].copy()
    data["auction_year"] = data["auction_year"].astype(int)
    data = data.drop_duplicates(subset=["player", "auction_year"], keep=False)
    if data.empty:
        raise ValueError("No valid, unique sold-player transactions remained after cleaning.")

    output.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(output, index=False)
    manifest_path = output.with_name("auction_history_metadata.json")
    manifest = {
        "verified": False,
        "verification_note": (
            "Review source provenance, reuse terms, sold-vs-unsold semantics, "
            "currency conversion, year coverage, duplicate transactions and player matching. "
            "Set verified=true only after manual review."
        ),
        "price_unit_after_conversion": "INR lakh",
        "sources": [{
            "name": source_name,
            "url": source_url,
            "license": "UNVERIFIED — review original source terms before use",
            "accessed_on": accessed_on,
            "declared_source_price_unit": price_unit,
        }],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return len(data), manifest_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", type=Path,
                        default=Path("data/processed/auction_history.csv"))
    parser.add_argument("--source-name", required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--price-unit", required=True,
                        choices=sorted(PRICE_TO_LAKH),
                        help="Unit of the source sold-price column; conversion is explicit.")
    parser.add_argument("--accessed-on", required=True, help="YYYY-MM-DD")
    args = parser.parse_args()
    count, manifest = prepare_auction_csv(
        args.input, args.output, source_name=args.source_name,
        source_url=args.source_url, price_unit=args.price_unit,
        accessed_on=args.accessed_on,
    )
    print(f"Prepared {count} sold-player rows at {args.output}")
    print(f"Created UNVERIFIED manifest at {manifest}")
    print("Review the manifest and source terms before enabling model training.")


if __name__ == "__main__":
    main()
