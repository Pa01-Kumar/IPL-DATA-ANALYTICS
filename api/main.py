from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / "api" / ".env")
DATA = ROOT / "data" / "processed"
app = FastAPI(title="IPL Intelligence API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def csv(name: str) -> pd.DataFrame:
    path = DATA / name
    if not path.exists():
        raise HTTPException(status_code=503, detail=f"Dataset unavailable: {name}")
    return pd.read_csv(path)

def records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    clean = frame.replace({np.nan: None, np.inf: None, -np.inf: None})
    return clean.to_dict(orient="records")

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "IPL Intelligence API"}

@app.get("/api/overview")
def overview():
    matches = csv("matches.csv")
    batting = csv("batting_stats.csv")
    impact = csv("player_impact.csv")
    season = (matches.dropna(subset=["season"]).groupby("season")
              .agg(matches=("match_id", "nunique"), teams=("team1", "nunique"))
              .reset_index())
    # IPL datasets may label the inaugural season as "2007/08" rather than 2008.
    # Sort and report season labels as strings instead of forcing them to integers.
    season["season_start"] = pd.to_numeric(
        season["season"].astype(str).str.extract(r"^(\d{4})")[0],
        errors="coerce",
    )
    season = season.sort_values(["season_start", "season"]).drop(columns=["season_start"])
    season_labels = season["season"].astype(str).tolist()
    wins = matches.dropna(subset=["winner"]).groupby("winner").size().sort_values(ascending=False).head(10)
    top_batters = batting.sort_values("runs", ascending=False).head(8)
    top_impact = impact.sort_values("combined_impact", ascending=False).head(8)
    return {
        "summary": {
            "matches": int(matches["match_id"].nunique()),
            "seasons": int(matches["season"].nunique()),
            "firstSeason": season_labels[0] if season_labels else None,
            "lastSeason": season_labels[-1] if season_labels else None,
            "players": int(len(impact)),
            "teams": int(pd.concat([matches["team1"], matches["team2"]]).nunique()),
        },
        "seasonTrend": records(season),
        "teamWins": [{"team": str(k), "wins": int(v)} for k, v in wins.items()],
        "topBatters": records(top_batters[["striker", "runs", "average", "strike_rate", "innings"]]),
        "topImpact": records(top_impact[["player", "role", "combined_impact", "rank"]]),
    }

@app.get("/api/players")
def players(search: str = "", role: str = "All", limit: int = Query(100, ge=1, le=500)):
    batting = csv("batting_stats.csv").rename(columns={"striker": "player"})
    bowling = csv("bowling_stats.csv").rename(columns={"bowler": "player"})
    impact = csv("player_impact.csv")
    frame = impact.merge(
        batting[["player", "runs", "average", "strike_rate", "innings", "fifties", "best_innings"]],
        on="player", how="left"
    ).merge(
        bowling[["player", "wickets", "economy", "bowl_sr", "legal_balls"]],
        on="player", how="left"
    )
    if search:
        frame = frame[frame["player"].str.contains(search, case=False, na=False)]
    if role != "All":
        frame = frame[frame["role"].str.contains(role, case=False, na=False)]
    frame = frame.sort_values("combined_impact", ascending=False).head(limit)
    return records(frame)

@app.get("/api/players/{player_name}")
def player_profile(player_name: str):
    result = players(search=player_name, limit=10)
    exact = [p for p in result if str(p["player"]).casefold() == player_name.casefold()]
    if not exact:
        raise HTTPException(status_code=404, detail="Player not found")
    return exact[0]

@app.get("/api/teams")
def teams():
    matches = csv("matches.csv")
    all_teams = sorted(set(matches["team1"].dropna()) | set(matches["team2"].dropna()))
    wins = matches.dropna(subset=["winner"]).groupby("winner").size().to_dict()
    played = pd.concat([matches["team1"], matches["team2"]]).value_counts().to_dict()
    return [{"team": t, "played": int(played.get(t, 0)), "wins": int(wins.get(t, 0)),
             "winRate": round(100 * wins.get(t, 0) / played.get(t, 1), 1)} for t in all_teams]

@app.get("/api/teams/compare")
def compare_teams(team_a: str, team_b: str):
    matches = csv("matches.csv")
    h2h = matches[
        ((matches["team1"] == team_a) & (matches["team2"] == team_b)) |
        ((matches["team1"] == team_b) & (matches["team2"] == team_a))
    ]
    return {
        "teamA": team_a, "teamB": team_b, "played": int(len(h2h)),
        "winsA": int((h2h["winner"] == team_a).sum()),
        "winsB": int((h2h["winner"] == team_b).sum()),
        "noResult": int(h2h["winner"].isna().sum()),
        "recent": records(h2h.sort_values("date", ascending=False).head(10)),
    }

@app.get("/api/venues")
def venues():
    matches = csv("matches.csv")
    venue = (matches.groupby("venue").agg(matches=("match_id", "nunique"),
             avg_first_score=("winner_runs", "mean")).reset_index()
             .sort_values("matches", ascending=False).head(30))
    return records(venue)

@app.get("/api/matchups")
def matchups(batter: str = "", bowler: str = "", limit: int = Query(50, ge=1, le=200)):
    frame = csv("matchups.csv")
    if batter:
        frame = frame[frame["striker"].str.contains(batter, case=False, na=False)]
    if bowler:
        frame = frame[frame["bowler"].str.contains(bowler, case=False, na=False)]
    return records(frame.sort_values("balls_faced", ascending=False).head(limit))

@app.get("/api/shortlist")
def shortlist(batting_priority: float = 0.8, bowling_priority: float = 0.8,
              allrounder_priority: float = 1.0, roles: str = "Batter,Bowler,All-rounder",
              limit: int = Query(15, ge=1, le=100)):
    from src.intelligence import load_player_intelligence, franchise_fit_scores
    frame = load_player_intelligence()
    ranked = franchise_fit_scores(frame, {
        "Batter": batting_priority, "Bowler": bowling_priority,
        "All-rounder": allrounder_priority,
    })
    selected = [r.strip() for r in roles.split(",") if r.strip()]
    ranked = ranked[ranked["fit_category"].isin(selected)].head(limit)
    return records(ranked)


@app.get("/api/win-probability/matches")
def win_probability_matches():
    matches = csv("matches.csv").dropna(subset=["winner"]).copy()
    matches["label"] = (
        matches["team1"].astype(str) + " vs " + matches["team2"].astype(str)
        + " · " + matches["date"].astype(str) + " · " + matches["match_id"].astype(str)
    )
    return records(matches[["match_id", "label", "winner", "team1", "team2", "date"]]
                   .sort_values("date", ascending=False))


@app.get("/api/win-probability/{match_id}")
def win_probability(match_id: str):
    delivery_path = DATA / "cleaned_deliveries.csv"
    model_path = ROOT / "models" / "winprob_logistic.pkl"
    if not delivery_path.exists() or not model_path.exists():
        raise HTTPException(status_code=503, detail="Win probability data or model unavailable")
    try:
        deliveries = pd.read_csv(delivery_path, dtype={"match_id": str}, low_memory=False)
        model_info = joblib.load(model_path)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Unable to load win probability resources: {exc}")
    md = deliveries[deliveries["match_id"].astype(str) == str(match_id)].copy()
    if md.empty or not (md["innings"] == 1).any() or not (md["innings"] == 2).any():
        raise HTTPException(status_code=404, detail="Match has no complete two-innings delivery record")
    target = float(md.loc[md["innings"] == 1, "total_runs"].sum()) + 1
    chase = md[md["innings"] == 2].copy().reset_index(drop=True)
    chase["runs_needed"] = target - chase["runs_so_far"]
    chase["balls_left"] = chase["balls_remaining"]
    chase["wickets_left"] = chase["wickets_in_hand"]
    balls_bowled = 120 - chase["balls_remaining"]
    chase["current_rr"] = np.where(balls_bowled > 0, chase["runs_so_far"] * 6 / balls_bowled, 0)
    chase["required_rr"] = np.where(chase["balls_remaining"] > 0,
                                    chase["runs_needed"] * 6 / chase["balls_remaining"], 0)
    chase["rrr_minus_crr"] = chase["required_rr"] - chase["current_rr"]
    chase["current_rr"] = chase["current_rr"].clip(0, 30)
    chase["required_rr"] = chase["required_rr"].clip(0, 30)
    chase["rrr_minus_crr"] = chase["rrr_minus_crr"].clip(-30, 30)
    chase = chase[(chase["balls_remaining"] >= 0) & (chase["runs_needed"] >= 0)].copy()
    if chase.empty:
        raise HTTPException(status_code=404, detail="No valid chase states for this match")
    features = model_info.get("features", [
        "runs_needed", "balls_left", "wickets_left",
        "current_rr", "required_rr", "rrr_minus_crr"
    ])
    try:
        x = model_info["scaler"].transform(chase[features].fillna(0))
        chase["wp"] = model_info["model"].predict_proba(x)[:, 1]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Win probability inference failed: {exc}")
    chase["ball_num"] = 120 - chase["balls_left"]
    columns = [c for c in [
        "over", "ball", "batting_team", "runs_so_far", "runs_needed",
        "balls_left", "wickets_left", "wp", "ball_num", "is_wicket"
    ] if c in chase.columns]
    winner_rows = csv("matches.csv")
    winner_rows = winner_rows[winner_rows["match_id"].astype(str) == str(match_id)]
    winner = None if winner_rows.empty else winner_rows.iloc[0]["winner"]
    batting_team = str(chase.iloc[-1]["batting_team"])
    return {
        "match_id": str(match_id),
        "target": int(target),
        "chasing_team": batting_team,
        "winner": None if pd.isna(winner) else str(winner),
        "last_valid_wp": float(chase.iloc[-1]["wp"]),
        "curve": records(chase[columns]),
    }

@app.get("/api/matches")
def matches(limit: int = Query(100, ge=1, le=500)):
    frame = csv("matches.csv").sort_values("date", ascending=False).head(limit)
    return records(frame)


# Live cricket provider proxy. API keys stay on the server and are never sent to the browser.
import os
import httpx

LIVE_PROVIDER_BASE = "https://api.cricketdatabase.com/v1"

@app.get("/api/live/status")
def live_status():
    configured = bool(os.getenv("CRICKET_DATABASE_API_KEY"))
    return {
        "configured": configured,
        "provider": "Cricket Database",
        "message": "Live feed connected" if configured else "Add CRICKET_DATABASE_API_KEY to api/.env to enable verified live scores.",
        "refresh_seconds": 20,
    }

async def live_provider_get(path: str, params: dict | None = None):
    key = os.getenv("CRICKET_DATABASE_API_KEY")
    if not key:
        raise HTTPException(status_code=503, detail="Live cricket provider is not configured. Add CRICKET_DATABASE_API_KEY to the API environment.")
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            response = await client.get(
                f"{LIVE_PROVIDER_BASE}{path}",
                headers={"Authorization": f"Bearer {key}"},
                params=params or {},
            )
        if response.status_code == 403:
            raise HTTPException(status_code=402, detail="The connected cricket data plan does not include this live endpoint.")
        if response.status_code == 429:
            raise HTTPException(status_code=429, detail="Live cricket provider rate limit reached. Please retry shortly.")
        if response.status_code == 401:
            raise HTTPException(status_code=502, detail="The configured cricket data key was rejected.")
        response.raise_for_status()
        return response.json()
    except HTTPException:
        raise
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Live cricket provider request failed: {exc}")

@app.get("/api/live/matches")
async def live_matches(state: str = Query("live", pattern="^(live|upcoming|finished|all)$"), format: str | None = None):
    params = {"state": state}
    if format:
        params["format"] = format
    return await live_provider_get("/live", params)

@app.get("/api/live/matches/{match_slug}")
async def live_match(match_slug: str):
    return await live_provider_get(f"/live/{match_slug}")
