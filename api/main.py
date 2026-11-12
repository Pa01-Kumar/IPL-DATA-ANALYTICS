from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

ROOT = Path(__file__).resolve().parents[1]
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

@app.get("/api/matches")
def matches(limit: int = Query(100, ge=1, le=500)):
    frame = csv("matches.csv").sort_values("date", ascending=False).head(limit)
    return records(frame)
