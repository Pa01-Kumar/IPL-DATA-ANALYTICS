# Historical IPL auction data

## Public research leads — not imported or verified as a training dataset

- IPL official auction pages: https://www.iplt20.com/auction/2026/sold
- Salary Sport, IPL 2025 auction: https://salarysport.com/cricket/ipl/auction/2025/
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

The metadata JSON must include:
```json
{
  "verified": true,
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
