"""IPL Intelligence player performance and franchise-fit analytics."""
from __future__ import annotations
from typing import Mapping
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
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

