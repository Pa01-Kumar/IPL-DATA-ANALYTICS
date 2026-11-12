from io import BytesIO
from pathlib import Path
import zipfile

import pandas as pd
import pytest

from src.build_consolidated import build_consolidated
from src.download_data import safe_extract_zip

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



def test_safe_extract_zip_extracts_valid_archive(tmp_path):
    archive_buffer = BytesIO()
    with zipfile.ZipFile(archive_buffer, "w") as archive:
        archive.writestr("match_123.csv", "ball,batter\n0.1,Player A\n")
    count = safe_extract_zip(archive_buffer.getvalue(), tmp_path)
    assert count == 1
    assert (tmp_path / "match_123.csv").is_file()


def test_safe_extract_zip_rejects_path_traversal(tmp_path):
    archive_buffer = BytesIO()
    with zipfile.ZipFile(archive_buffer, "w") as archive:
        archive.writestr("../outside.txt", "not allowed")
    with pytest.raises(ValueError, match="Unsafe archive member path"):
        safe_extract_zip(archive_buffer.getvalue(), tmp_path)
    assert not (tmp_path.parent / "outside.txt").exists()


def test_build_consolidated_combines_match_files(tmp_path):
    pd.DataFrame({"ball": ["0.1"], "batter": ["Player A"]}).to_csv(
        tmp_path / "match_1.csv", index=False)
    pd.DataFrame({"ball": ["0.2"], "batter": ["Player B"]}).to_csv(
        tmp_path / "match_2.csv", index=False)
    pd.DataFrame({"meta": ["ignore"]}).to_csv(
        tmp_path / "match_1_info.csv", index=False)
    output = build_consolidated(tmp_path)
    result = pd.read_csv(output, dtype={"match_id": str})
    assert len(result) == 2
    assert set(result["match_id"]) == {"match_1", "match_2"}


def test_build_consolidated_reports_empty_directory(tmp_path):
    with pytest.raises(FileNotFoundError, match="No per-match delivery CSV"):
        build_consolidated(tmp_path)



def test_specialist_fit_uses_role_specific_impact_only():
    players = pd.DataFrame([
        {"player": "Batter", "role": "Batter", "batting_impact": 40,
         "bowling_impact": 95, "combined_impact": 90},
        {"player": "Bowler", "role": "Bowler", "batting_impact": 95,
         "bowling_impact": 40, "combined_impact": 90},
        {"player": "All-rounder", "role": "All-rounder", "batting_impact": 40,
         "bowling_impact": 40, "combined_impact": 65},
    ])
    ranked = franchise_fit_scores(
        players, {"Batter": 1, "Bowler": 1, "All-rounder": 1}
    ).set_index("player")
    assert ranked.loc["Batter", "franchise_fit_score"] == 0.4
    assert ranked.loc["Bowler", "franchise_fit_score"] == 0.4
    assert ranked.loc["All-rounder", "franchise_fit_score"] == 0.65
