"""IPL Intelligence analytics and auction-price safeguards."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Mapping
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
AUCTION_FILE = PROCESSED / "auction_history.csv"
AUCTION_METADATA = PROCESSED / "auction_history_metadata.json"
PRE_AUCTION_FEATURES = {
    "role", "age", "overseas", "country", "capped_status",
    "prior_runs", "prior_average", "prior_strike_rate", "prior_wickets",
    "prior_economy", "prior_matches", "prior_balls_faced", "prior_legal_balls",
}

def load_player_intelligence() -> pd.DataFrame:
    batting = pd.read_csv(PROCESSED / "batting_stats.csv").rename(columns={"striker": "player"})
    bowling = pd.read_csv(PROCESSED / "bowling_stats.csv").rename(columns={"bowler": "player"})
    impact = pd.read_csv(PROCESSED / "player_impact.csv")
    # Select only performance columns: keep the impact table's role column authoritative.
    result = impact.merge(
        batting[["player", "runs", "average", "strike_rate", "innings",
                 "SR_Powerplay", "SR_Middle", "SR_Death"]],
        on="player", how="left", validate="one_to_one"
    ).merge(
        bowling[["player", "wickets", "economy", "bowl_sr", "legal_balls"]],
        on="player", how="left", validate="one_to_one"
    )
    return result

def franchise_fit_scores(players: pd.DataFrame, role_needs: Mapping[str, float]) -> pd.DataFrame:
    frame = players.copy()
    required = {"role", "batting_impact", "bowling_impact", "combined_impact"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Player intelligence is missing columns: {', '.join(sorted(missing))}")
    weights = {k: float(role_needs.get(k, 0)) for k in ("Batter", "Bowler", "All-rounder")}
    if any(not 0 <= v <= 1 for v in weights.values()):
        raise ValueError("Role priorities must be between 0 and 1.")
    role = frame["role"].fillna("Unclassified").astype(str)
    batting = pd.to_numeric(frame["batting_impact"], errors="coerce").fillna(0)
    bowling = pd.to_numeric(frame["bowling_impact"], errors="coerce").fillna(0)
    combined = pd.to_numeric(frame["combined_impact"], errors="coerce").fillna(0)
    is_bowler = role.str.contains("Bowler", case=False)
    is_allrounder = role.str.contains("All-rounder", case=False)
    is_batter = ~(is_bowler | is_allrounder)
    category_weight = np.select(
        [is_bowler, is_allrounder, is_batter],
        [weights["Bowler"], weights["All-rounder"], weights["Batter"]], default=0.0)
    impact_score = np.where(is_bowler, bowling,
                            np.where(is_allrounder, combined, np.maximum(batting, combined * .65)))
    frame["franchise_fit_score"] = (impact_score * category_weight / 100).round(2)
    frame["fit_category"] = np.select(
        [is_bowler, is_allrounder, is_batter],
        ["Bowler", "All-rounder", "Batter"], default="Unclassified")
    return frame.sort_values(["franchise_fit_score", "combined_impact"],
                             ascending=False).reset_index(drop=True)

def auction_dataset_status(path: Path = AUCTION_FILE,
                           metadata_path: Path = AUCTION_METADATA) -> tuple[bool, str]:
    if not path.exists():
        return False, "Verified historical auction transactions are not installed."
    if not metadata_path.exists():
        return False, "Auction provenance manifest is missing; source/license verification is required."
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        data = pd.read_csv(path)
    except Exception as exc:
        return False, f"Could not validate auction data or metadata: {exc}"
    required = {"player", "auction_year", "sold_price_lakh"}
    missing = required - set(data.columns)
    if missing:
        return False, "Auction history is missing required columns: " + ", ".join(sorted(missing))
    if metadata.get("verified") is not True:
        return False, "Auction data is not manually verified in its provenance manifest."
    review_flags = ("sold_only", "currency_reviewed", "coverage_reviewed",
                    "player_matching_reviewed", "duplicate_reviewed", "reuse_rights_reviewed")
    if any(metadata.get(flag) is not True for flag in review_flags):
        return False, "Manifest must confirm sold-only records, currency, coverage, player matching, duplicates and reuse rights."
    if metadata.get("price_unit_after_conversion") != "INR lakh":
        return False, "Manifest must confirm that sold prices are normalized to INR lakh."
    sources = metadata.get("sources", [])
    if not sources or any(not all(s.get(k) for k in ("name", "url", "license", "accessed_on"))
                          for s in sources):
        return False, "Manifest must document source name, URL, license/terms and access date."
    years = pd.to_numeric(data["auction_year"], errors="coerce").dropna().unique()
    prices = pd.to_numeric(data["sold_price_lakh"], errors="coerce")
    if len(years) < 2:
        return False, "At least two auction years are required for a temporal holdout."
    if prices.isna().any() or (prices <= 0).any():
        return False, "Sold prices must be numeric, positive INR lakh values."
    if data["player"].isna().any():
        return False, "Every transaction must have a player name."
    return True, f"Verified dataset accepted: {len(data)} transactions across {len(years)} years."

def train_auction_price_model(path: Path = AUCTION_FILE,
                              metadata_path: Path = AUCTION_METADATA):
    ready, message = auction_dataset_status(path, metadata_path)
    if not ready:
        raise ValueError(message)
    from sklearn.compose import ColumnTransformer
    from sklearn.impute import SimpleImputer
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler
    from sklearn.ensemble import RandomForestRegressor
    data = pd.read_csv(path)
    data["auction_year"] = pd.to_numeric(data["auction_year"], errors="coerce")
    data["sold_price_lakh"] = pd.to_numeric(data["sold_price_lakh"], errors="coerce")
    data = data.dropna(subset=["auction_year", "sold_price_lakh"]).copy()
    years = sorted(data["auction_year"].unique())
    features = [c for c in data.columns if c in PRE_AUCTION_FEATURES and data[c].notna().any()]
    if not features:
        raise ValueError("No approved pre-auction predictor columns were found.")
    train, test = data[data.auction_year < years[-1]], data[data.auction_year == years[-1]]
    if len(train) < 10 or test.empty:
        raise ValueError("Need at least 10 earlier auction records and one latest-year record.")
    numeric = [c for c in features if pd.api.types.is_numeric_dtype(data[c])]
    categorical = [c for c in features if c not in numeric]
    transformers = []
    if numeric:
        transformers.append(("numeric", Pipeline([
            ("imputer", SimpleImputer(strategy="median")), ("scale", StandardScaler())]), numeric))
    if categorical:
        transformers.append(("categorical", Pipeline([
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore"))]), categorical))
    model = Pipeline([
        ("preprocess", ColumnTransformer(transformers)),
        ("regressor", RandomForestRegressor(n_estimators=300, min_samples_leaf=2,
                                            random_state=42, n_jobs=-1))])
    model.fit(train[features], train["sold_price_lakh"])
    pred = model.predict(test[features])
    metrics = {
        "holdout_year": int(years[-1]), "records_train": int(len(train)),
        "records_test": int(len(test)),
        "mae_lakh": float(mean_absolute_error(test["sold_price_lakh"], pred)),
        "rmse_lakh": float(np.sqrt(mean_squared_error(test["sold_price_lakh"], pred))),
        "r2": float(r2_score(test["sold_price_lakh"], pred)) if len(test) > 1 else None,
        "features": features,
    }
    return model, metrics
