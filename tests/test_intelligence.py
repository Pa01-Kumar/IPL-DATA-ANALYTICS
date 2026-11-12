import pandas as pd

from src.intelligence import franchise_fit_scores


def test_franchise_fit_scores_ranks_role_need():
    players = pd.DataFrame([
        {"player": "Batter A", "role": "Batter", "batting_impact": 80,
         "bowling_impact": 0, "combined_impact": 80},
        {"player": "Bowler B", "role": "Bowler", "batting_impact": 0,
         "bowling_impact": 75, "combined_impact": 75},
    ])
    ranked = franchise_fit_scores(
        players, {"Batter": 1, "Bowler": 0.2, "All-rounder": 0.5}
    )
    assert ranked.iloc[0]["player"] == "Batter A"
    assert ranked["franchise_fit_score"].notna().all()


def test_zero_role_need_produces_zero_fit():
    players = pd.DataFrame([
        {"player": "Player A", "role": "Batter", "batting_impact": 50,
         "bowling_impact": 0, "combined_impact": 50},
    ])
    ranked = franchise_fit_scores(
        players, {"Batter": 0, "Bowler": 0, "All-rounder": 0}
    )
    assert ranked.iloc[0]["franchise_fit_score"] == 0
