"""Transparent analytics helpers for IPL Intelligence.

Auction-price training is deliberately gated on verified historical auction records.
Cricsheet match data alone is not auction transaction data.
"""
from __future__ import annotations

from pathlib import Path
from typing import Mapping

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
AUCTION_FILE = PROCESSED / "auction_history.csv"


def load_player_intelligence() -> pd.DataFrame:
    """Combine the project's existing batting, bowling and impact tables."""
    batting = pd.read_csv(PROCESSED / "batting_stats.csv")
    bowling = pd.read_csv(PROCESSED / "bowling_stats.csv")
    impact = pd.read_csv(PROCESSED / "player_impact.csv")

    batting = batting.rename(columns={"striker": "player"})
    bowling = bowling.rename(columns={"bowler": "player"})
    result = impact.merge(
        batting[["player", "runs", "average", "strike_rate", "innings",
                 "SR_Powerplay", "SR_Middle", "SR_Death"]],
        on="player", how="left"
    ).merge(
        bowling[["player", "wickets", "economy", "bowl_sr", "legal_balls"]],
        on="player", how="left"
    )
    return result


def franchise_fit_scores(players: pd.DataFrame,
                         role_needs: Mapping[str, float]) -> pd.DataFrame:
    """Rank players against analyst-defined role priorities (not real squad data)."""
    frame = players.copy()
    weights = {
        "Batter": float(role_needs.get("Batter", 0)),
        "Bowler": float(role_needs.get("Bowler", 0)),
        "All-rounder": float(role_needs.get("All-rounder", 0)),
    }
    role = frame["role"].fillna("Unclassified").astype(str)
    batting = pd.to_numeric(frame["batting_impact"], errors="coerce").fillna(0)
    bowling = pd.to_numeric(frame["bowling_impact"], errors="coerce").fillna(0)
    combined = pd.to_numeric(frame["combined_impact"], errors="coerce").fillna(0)

    # Convert role labels in the source to broad squad categories.
    is_bowler = role.str.contains("Bowler", case=False)
    is_allrounder = role.str.contains("All-rounder", case=False)
    is_batter = ~(is_bowler | is_allrounder)
    category_weight = np.select(
        [is_bowler, is_allrounder, is_batter],
        [weights["Bowler"], weights["All-rounder"], weights["Batter"]],
        default=0.0,
    )
    impact = np.where(is_bowler, bowling, np.where(is_allrounder, combined,
                                                    np.maximum(batting, combined * 0.65)))
    frame["franchise_fit_score"] = (impact * category_weight / 100).round(2)
    frame["fit_category"] = np.select(
        [is_bowler, is_allrounder, is_batter],
        ["Bowler", "All-rounder", "Batter"], default="Unclassified"
    )
    return frame.sort_values(
        ["franchise_fit_score", "combined_impact"], ascending=False
    ).reset_index(drop=True)


def auction_dataset_status(path: Path = AUCTION_FILE) -> tuple[bool, str]:
    """Check whether a real auction dataset is available and minimally valid."""
    if not path.exists():
        return False, (
            "Historical auction transactions are not included yet. Add a verified "
            "auction_history.csv with auction_year and sold_price_lakh columns "
            "before training a price model."
        )
    try:
        sample = pd.read_csv(path, nrows=5)
    except Exception as exc:
        return False, f"Could not read auction history: {exc}"
    required = {"auction_year", "sold_price_lakh"}
    missing = required - set(sample.columns)
    if missing:
        return False, "Auction history is missing required columns: " + ", ".join(sorted(missing))
    return True, "Auction history schema found. Validate source, coverage and player matching before training."


def train_auction_price_model(path: Path = AUCTION_FILE):
    """Train a temporal holdout model only when real auction outcomes are supplied.

    Expected columns: auction_year, sold_price_lakh. Optional predictors can
    include role, age, overseas, runs, average, strike_rate, wickets, economy,
    and franchise. The final auction year is held out for evaluation.
    """
    from sklearn.compose import ColumnTransformer
    from sklearn.impute import SimpleImputer
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler
    from sklearn.ensemble import RandomForestRegressor

    data = pd.read_csv(path)
    required = {"auction_year", "sold_price_lakh"}
    if not required.issubset(data.columns):
        raise ValueError("auction_history.csv needs auction_year and sold_price_lakh")
    data = data.dropna(subset=["auction_year", "sold_price_lakh"]).copy()
    data["auction_year"] = pd.to_numeric(data["auction_year"], errors="coerce")
    data["sold_price_lakh"] = pd.to_numeric(data["sold_price_lakh"], errors="coerce")
    data = data.dropna(subset=["auction_year", "sold_price_lakh"])
    years = sorted(data["auction_year"].unique())
    if len(years) < 2:
        raise ValueError("At least two auction seasons are required for a temporal holdout.")

    target = "sold_price_lakh"
    excluded = {target, "player", "player_name", "auction_year", "status"}
    candidates = [c for c in data.columns if c not in excluded]
    features = [c for c in candidates if data[c].notna().any()]
    if not features:
        raise ValueError("No usable player/franchise predictor columns were found.")
    train = data[data["auction_year"] < years[-1]]
    test = data[data["auction_year"] == years[-1]]
    if len(train) < 10 or test.empty:
        raise ValueError("Need at least 10 earlier auction records and one latest-year record.")

    numeric = [c for c in features if pd.api.types.is_numeric_dtype(data[c])]
    categorical = [c for c in features if c not in numeric]
    transformers = []
    if numeric:
        transformers.append(("numeric", Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
        ]), numeric))
    if categorical:
        transformers.append(("categorical", Pipeline([
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]), categorical))
    prep = ColumnTransformer(transformers)
    model = Pipeline([
        ("preprocess", prep),
        ("regressor", RandomForestRegressor(
            n_estimators=300, min_samples_leaf=2, random_state=42,
            n_jobs=-1
        )),
    ])
    model.fit(train[features], train[target])
    prediction = model.predict(test[features])
    metrics = {
        "holdout_year": int(years[-1]),
        "records_train": int(len(train)),
        "records_test": int(len(test)),
        "mae_lakh": float(mean_absolute_error(test[target], prediction)),
        "rmse_lakh": float(np.sqrt(mean_squared_error(test[target], prediction))),
        "r2": float(r2_score(test[target], prediction)) if len(test) > 1 else None,
    }
    return model, metrics
