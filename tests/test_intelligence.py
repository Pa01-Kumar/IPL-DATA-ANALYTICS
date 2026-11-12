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
        {"player": "Batting AR", "role": "Batting all-rounder", "batting_impact": 55,
         "bowling_impact": 35, "combined_impact": 65},
        {"player": "Bowling AR", "role": "Bowling all-rounder", "batting_impact": 25,
         "bowling_impact": 60, "combined_impact": 65},
    ])
    ranked = franchise_fit_scores(
        players, {"Batter": 1, "Bowler": 1, "All-rounder": 1}
    )
    assert set(ranked["fit_category"]) == {"Batter", "Bowler", "All-rounder"}
    assert set(ranked.loc[ranked["player"].isin(["Allrounder", "Batting AR", "Bowling AR"]),
                          "fit_category"]) == {"All-rounder"}



def test_load_player_intelligence_uses_impact_role_without_merge_collision(tmp_path):
    pd.DataFrame([{
        "striker": "Player A", "runs": 500, "average": 30.0,
        "strike_rate": 140.0, "innings": 20, "SR_Powerplay": 120.0,
        "SR_Middle": 140.0, "SR_Death": 180.0, "role": "Anchor",
    }]).to_csv(tmp_path / "batting_stats.csv", index=False)
    pd.DataFrame([{
        "bowler": "Player A", "wickets": 10, "economy": 8.0,
        "bowl_sr": 18.0, "legal_balls": 180,
    }]).to_csv(tmp_path / "bowling_stats.csv", index=False)
    pd.DataFrame([{
        "player": "Player A", "batting_impact": 70.0,
        "bowling_impact": 10.0, "combined_impact": 75.0,
        "role": "All-rounder",
    }]).to_csv(tmp_path / "player_impact.csv", index=False)

    result = load_player_intelligence(data_dir=tmp_path)
    assert len(result) == 1
    assert result.loc[0, "role"] == "All-rounder"
    assert result.loc[0, "runs"] == 500
    assert result.loc[0, "wickets"] == 10


def test_load_player_intelligence_rejects_duplicate_player_rows(tmp_path):
    batting = pd.DataFrame([
        {"striker": "Player A", "runs": 100, "average": 20,
         "strike_rate": 100, "innings": 5, "SR_Powerplay": 100,
         "SR_Middle": 100, "SR_Death": 100},
        {"striker": "Player A", "runs": 200, "average": 25,
         "strike_rate": 110, "innings": 6, "SR_Powerplay": 100,
         "SR_Middle": 110, "SR_Death": 120},
    ])
    batting.to_csv(tmp_path / "batting_stats.csv", index=False)
    pd.DataFrame([{"bowler": "Player A", "wickets": 1, "economy": 8,
                   "bowl_sr": 20, "legal_balls": 20}]).to_csv(
        tmp_path / "bowling_stats.csv", index=False)
    pd.DataFrame([{"player": "Player A", "batting_impact": 10,
                   "bowling_impact": 1, "combined_impact": 10,
                   "role": "Batter"}]).to_csv(tmp_path / "player_impact.csv", index=False)
    with pytest.raises(ValueError, match="duplicate player"):
        load_player_intelligence(data_dir=tmp_path)


def test_load_player_intelligence_reports_missing_files(tmp_path):
    with pytest.raises(FileNotFoundError, match="Required player dataset"):
        load_player_intelligence(data_dir=tmp_path)
