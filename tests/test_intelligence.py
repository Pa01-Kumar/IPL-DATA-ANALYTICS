import pandas as pd
import pytest

from src.intelligence import franchise_fit_scores, load_player_intelligence


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
    players = pd.DataFrame([{
        "player": "A", "role": "Batter", "batting_impact": 50,
        "bowling_impact": 0, "combined_impact": 50,
    }])
    ranked = franchise_fit_scores(
        players, {"Batter": 0, "Bowler": 0, "All-rounder": 0}
    )
    assert ranked.iloc[0]["franchise_fit_score"] == 0


def test_role_priority_out_of_range_is_rejected():
    players = pd.DataFrame([{
        "player": "A", "role": "Batter", "batting_impact": 50,
        "bowling_impact": 0, "combined_impact": 50,
    }])
    with pytest.raises(ValueError):
        franchise_fit_scores(players, {"Batter": 1.5})


def test_role_categories_are_assigned():
    players = pd.DataFrame([
        {"player": "Batter", "role": "Batter", "batting_impact": 60,
         "bowling_impact": 0, "combined_impact": 60},
        {"player": "Bowler", "role": "Bowler", "batting_impact": 0,
         "bowling_impact": 70, "combined_impact": 70},
        {"player": "Allrounder", "role": "All-rounder", "batting_impact": 55,
         "bowling_impact": 50, "combined_impact": 65},
    ])
    ranked = franchise_fit_scores(
        players, {"Batter": 1, "Bowler": 1, "All-rounder": 1}
    )
    assert set(ranked["fit_category"]) == {"Batter", "Bowler", "All-rounder"}
