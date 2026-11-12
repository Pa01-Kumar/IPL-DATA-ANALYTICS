# Historical IPL auction data

## Public research leads — not imported or verified as a training dataset

- IPL official auction pages: https://www.iplt20.com/auction/2026/sold
- Salary Sport, IPL 2025 auction: https://salarysport.com/cricket/ipl/auction/2025/
- Foridur3210's [IPL IMB381IPL2013.csv](https://github.com/Foridur3210/IPL-Dataset-Player-price-prediction/blob/master/IPL%20IMB381IPL2013.csv) has 130 rows and historical auction years, but its sold-price unit and original reuse terms need confirmation before use.
- [2023 IPL squad/auction dataset](https://github.com/ramdhote05/IPL-AUCTION-DATA-ANALYSIS) contains rupee-crore cost fields alongside retained-player rows; exclude retained entries and independently verify sold status and license before import.
- Outside Edge historical acquisition analysis: https://github.com/outside-edge/ipl_auction (its README describes Kaggle, Wikipedia and IPL official sources, and notes a 2024 data gap)
- Times of India, IPL 2025 sold-player list: https://timesofindia.indiatimes.com/sports/cricket/ipl/top-stories/ipl-auction-2025-full-list-of-sold-players-of-all-teams/articleshow/115618338.cms

These are research leads only. Public visibility does not automatically permit redistribution. Inspect original records, coverage and reuse terms before importing anything. A single season is not sufficient for a temporal train/test evaluation.

## Required project files

Place cleaned transactions at `data/processed/auction_history.csv` and a provenance manifest at `data/processed/auction_history_metadata.json`.

CSV required columns:
- `player`: normalized player name
- `auction_year`: numeric auction year
- `sold_price_lakh`: final sold price in INR lakh, not base price

Only pre-auction predictors allowlisted in `src/intelligence.py` can be used (for example role, age, overseas status and prior-season performance). Post-sale franchise/team, winning bid fields and future performance are excluded.

## Prepare a source CSV

Use the importer to normalize a downloaded source file. It deliberately discards franchise/team and other unapproved columns, and writes an **unverified** manifest. Declare the original price unit explicitly; do not guess or mix currencies.

```bash
python src/prepare_auction_data.py --input /path/to/source.csv --source-name "Publisher or dataset" --source-url "https://source.example/data" --price-unit inr --accessed-on 2026-11-13
```

Accepted price units are `inr`, `inr-lakh`, and `inr-crore`. The importer converts to INR lakh. It supports common source headings such as `PLAYER NAME`, `AUCTION YEAR`, `SOLD PRICE`, and `PLAYING ROLE`. It does not infer USD or other currency conversions.

The generated manifest starts with `verified: false`. Before enabling training, manually review and set all of these flags to true only when supported by the source: `sold_only`, `currency_reviewed`, `coverage_reviewed`, `player_matching_reviewed`, `duplicate_reviewed`, and `reuse_rights_reviewed`. Also set `price_unit_after_conversion` to `INR lakh` and document the exact source license/terms. The code checks these flags, but cannot independently prove the truth of a manual declaration.

The metadata JSON must include:
```json
{
  "verified": true,
  "price_unit_after_conversion": "INR lakh",
  "sold_only": true,
  "currency_reviewed": true,
  "coverage_reviewed": true,
  "player_matching_reviewed": true,
  "duplicate_reviewed": true,
  "reuse_rights_reviewed": true,
  "sources": [
    {
      "name": "Publisher or dataset name",
      "url": "https://source.example/data",
      "license": "Exact license or terms of use",
      "accessed_on": "YYYY-MM-DD"
    }
  ]
}
```

Set `verified` to true only after manually checking provenance, redistribution terms, year coverage, currency, sold-vs-unsold status, player matching and duplicate transactions. Record each source. Never use illustrative data as a real transaction.

The app remains gated without both files and a valid manifest. It requires at least two auction years and at least 10 earlier training records. The latest year is held out. Report MAE/RMSE only after evaluation runs on the verified dataset.
