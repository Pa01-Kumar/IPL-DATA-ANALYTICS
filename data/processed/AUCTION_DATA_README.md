# Historical IPL auction data

This folder intentionally does not contain fabricated auction prices.

To enable the price-prediction module, place a verified, properly licensed
historical transaction dataset at:

    data/processed/auction_history.csv

Required columns:
- auction_year: numeric IPL auction year
- sold_price_lakh: final sold price in INR lakh

Recommended player predictors (when reliably sourced):
- role, age, overseas, runs, average, strike_rate
- wickets, economy, franchise

Keep unsold/withdrawn records separate from sold-price regression unless the
model explicitly treats auction status as a separate classification task.
Document source URLs, access date, license/terms, player-name matching rules,
currency units, and missing-value treatment. Do not mix base price with sold
price. A model must be evaluated on a later auction year not used for training.
