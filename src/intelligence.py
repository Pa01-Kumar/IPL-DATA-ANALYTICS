"""IPL Intelligence player performance and franchise-fit analytics."""
from __future__ import annotations
from typing import Mapping
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
def load_player_intelligence(data_dir=None) -> pd.DataFrame:
    """Load and join the three processed player tables with explicit schema checks.

    data_dir is injectable for tests; production defaults to data/processed.
    """
    data_dir = Path(data_dir) if data_dir is not None else PROCESSED
    batting_path = data_dir / "batting_stats.csv"
    bowling_path = data_dir / "bowling_stats.csv"
    impact_path = data_dir / "player_impact.csv"
    for path in (batting_path, bowling_path, impact_path):
        if not path.is_file():
            raise FileNotFoundError(f"Required player dataset not found: {path}")

    batting = pd.read_csv(batting_path).rename(columns={"striker": "player"})
    bowling = pd.read_csv(bowling_path).rename(columns={"bowler": "player"})
    impact = pd.read_csv(impact_path)
    required = {
        "batting": (batting, {"player", "runs", "average", "strike_rate", "innings",
                              "SR_Powerplay", "SR_Middle", "SR_Death"}),
        "bowling": (bowling, {"player", "wickets", "economy", "bowl_sr", "legal_balls"}),
        "impact": (impact, {"player", "role", "batting_impact", "bowling_impact",
                            "combined_impact"}),
    }
    for label, (frame, columns) in required.items():
        missing = columns - set(frame.columns)
        if missing:
            raise ValueError(f"{label} dataset is missing columns: {', '.join(sorted(missing))}")
        if frame["player"].duplicated().any():
            raise ValueError(f"{label} dataset contains duplicate player rows")

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
    is_allrounder = role.str.contains(r"all[\s-]?rounder", case=False, regex=True)
    is_bowler = role.str.contains("Bowler", case=False) & ~is_allrounder
    is_batter = ~(is_bowler | is_allrounder)
    category_weight = np.select(
        [is_bowler, is_allrounder, is_batter],
        [weights["Bowler"], weights["All-rounder"], weights["Batter"]], default=0.0)
    # Use the impact measure that matches each player's role; avoid allowing
    # a high combined score to inflate a specialist batter's batting fit.
    impact_score = np.where(is_bowler, bowling,
                            np.where(is_allrounder, combined, batting))
    frame["franchise_fit_score"] = (impact_score * category_weight / 100).round(2)
    frame["fit_category"] = np.select(
        [is_bowler, is_allrounder, is_batter],
        ["Bowler", "All-rounder", "Batter"], default="Unclassified")
    return frame.sort_values(["franchise_fit_score", "combined_impact"],
                             ascending=False).reset_index(drop=True)

