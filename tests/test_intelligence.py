import json
import pandas as pd
import pytest
from src.intelligence import auction_dataset_status, franchise_fit_scores, train_auction_price_model
from src.prepare_auction_data import prepare_auction_csv

def test_franchise_fit_scores_ranks_role_need():
    players = pd.DataFrame([
        {"player":"Batter A","role":"Batter","batting_impact":80,"bowling_impact":0,"combined_impact":80},
        {"player":"Bowler B","role":"Bowler","batting_impact":0,"bowling_impact":75,"combined_impact":75},
    ])
    ranked = franchise_fit_scores(players, {"Batter":1,"Bowler":.2,"All-rounder":.5})
    assert ranked.iloc[0]["player"] == "Batter A"
    assert ranked["franchise_fit_score"].notna().all()

def test_zero_role_need_produces_zero_fit():
    players = pd.DataFrame([{"player":"A","role":"Batter","batting_impact":50,"bowling_impact":0,"combined_impact":50}])
    ranked = franchise_fit_scores(players, {"Batter":0,"Bowler":0,"All-rounder":0})
    assert ranked.iloc[0]["franchise_fit_score"] == 0

def test_role_priority_out_of_range_is_rejected():
    players = pd.DataFrame([{"player":"A","role":"Batter","batting_impact":50,"bowling_impact":0,"combined_impact":50}])
    with pytest.raises(ValueError):
        franchise_fit_scores(players, {"Batter":1.5})

def write_auction_files(tmp_path, manifest=True):
    rows = [{"player":f"Player {i}","auction_year":2022+i//10,
             "sold_price_lakh":50+i,"prior_runs":100+i,"franchise":"Team A"} for i in range(20)]
    csv_path = tmp_path/"auction_history.csv"
    pd.DataFrame(rows).to_csv(csv_path,index=False)
    manifest_path = tmp_path/"auction_history_metadata.json"
    if manifest:
        manifest_path.write_text(json.dumps({"verified":True,"price_unit_after_conversion":"INR lakh",
            "sold_only":True,"currency_reviewed":True,"coverage_reviewed":True,
            "player_matching_reviewed":True,"duplicate_reviewed":True,
            "reuse_rights_reviewed":True,"sources":[{
            "name":"Test source","url":"https://example.org/data","license":"Test terms",
            "accessed_on":"2026-11-13"}]}),encoding="utf-8")
    return csv_path,manifest_path

def test_auction_data_requires_provenance_manifest(tmp_path):
    csv_path,manifest_path = write_auction_files(tmp_path,manifest=False)
    ready,message = auction_dataset_status(csv_path,manifest_path)
    assert not ready and "manifest" in message.lower()

def test_auction_training_uses_only_allowlisted_preauction_features(tmp_path):
    csv_path,manifest_path = write_auction_files(tmp_path)
    _,metrics = train_auction_price_model(csv_path,manifest_path)
    assert metrics["holdout_year"] == 2023
    assert metrics["records_train"] == 10 and metrics["records_test"] == 10
    assert metrics["features"] == ["prior_runs"]
    assert "franchise" not in metrics["features"]

def test_auction_data_rejects_nonpositive_prices(tmp_path):
    csv_path,manifest_path = write_auction_files(tmp_path)
    data = pd.read_csv(csv_path)
    data.loc[0,"sold_price_lakh"] = 0
    data.to_csv(csv_path,index=False)
    ready,message = auction_dataset_status(csv_path,manifest_path)
    assert not ready and "positive" in message.lower()


def test_prepare_auction_csv_normalizes_price_and_drops_post_sale_team(tmp_path):
    source = tmp_path / "source.csv"
    pd.DataFrame([
        {"PLAYER NAME": "Player A", "AUCTION YEAR": 2022,
         "SOLD PRICE": 25000000, "PLAYING ROLE": "Batsman", "TEAM": "Team X"},
        {"PLAYER NAME": "Player B", "AUCTION YEAR": 2023,
         "SOLD PRICE": 50000000, "PLAYING ROLE": "Bowler", "TEAM": "Team Y"},
    ]).to_csv(source, index=False)
    output = tmp_path / "auction_history.csv"
    count, manifest_path = prepare_auction_csv(
        source, output, source_name="Example", source_url="https://example.org",
        price_unit="inr", accessed_on="2026-11-13")
    result = pd.read_csv(output)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert count == 2
    assert result["sold_price_lakh"].tolist() == [250.0, 500.0]
    assert "TEAM" not in result.columns and "franchise" not in result.columns
    assert manifest["verified"] is False

def test_prepare_auction_csv_rejects_unknown_price_unit(tmp_path):
    source = tmp_path / "source.csv"
    pd.DataFrame([{"player": "A", "auction_year": 2022, "sold_price": 10}]).to_csv(source, index=False)
    with pytest.raises(KeyError):
        prepare_auction_csv(
            source, tmp_path / "out.csv", source_name="Example",
            source_url="https://example.org", price_unit="usd",
            accessed_on="2026-11-13")
