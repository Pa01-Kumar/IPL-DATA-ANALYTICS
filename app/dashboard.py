"""
IPL Performance & Decision Analytics — Streamlit Dashboard
Run: streamlit run app/dashboard.py
"""
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import pickle
from pathlib import Path

st.set_page_config(page_title="IPL Analytics", page_icon="🏏", layout="wide")

ROOT   = Path(__file__).resolve().parent.parent
DATA   = ROOT / "data" / "processed"
MODELS = ROOT / "models"

# ---------------- data loaders (cached) ----------------
@st.cache_data
def load_batting():   return pd.read_csv(DATA / "batting_stats.csv")
@st.cache_data
def load_bowling():   return pd.read_csv(DATA / "bowling_stats.csv")
@st.cache_data
def load_impact():    return pd.read_csv(DATA / "player_impact.csv")
@st.cache_data
def load_matches():   return pd.read_csv(DATA / "matches.csv", dtype={"match_id": str})
@st.cache_data
def load_deliveries():
    return pd.read_csv(DATA / "cleaned_deliveries.csv",
                       dtype={"ball": str, "match_id": str}, low_memory=False)
@st.cache_data
def load_matchups():
    p = DATA / "matchups.csv"
    return pd.read_csv(p) if p.exists() else None

@st.cache_resource
def load_wp():
    with open(MODELS / "winprob_logistic.pkl", "rb") as f:
        return pickle.load(f)

FEATURES = ["runs_needed", "balls_left", "wickets_left",
            "current_rr", "required_rr", "rrr_minus_crr"]

def compute_wp_curve(match_id):
    wp_pkl = load_wp()
    d = load_deliveries()
    md = d[d["match_id"] == match_id]
    if md.empty: return None
    first = md[md["innings"] == 1]["total_runs"].sum()
    c = md[md["innings"] == 2].copy().reset_index(drop=True)
    c["runs_needed"]   = (first + 1) - c["runs_so_far"]
    c["balls_left"]    = c["balls_remaining"]
    c["wickets_left"]  = c["wickets_in_hand"]
    bb = 120 - c["balls_remaining"]
    c["current_rr"]    = np.where(bb > 0, c["runs_so_far"] * 6 / bb, 0)
    c["required_rr"]   = np.where(c["balls_remaining"] > 0,
                                  c["runs_needed"] * 6 / c["balls_remaining"], 0)
    c["rrr_minus_crr"] = c["required_rr"] - c["current_rr"]
    c["current_rr"]    = c["current_rr"].clip(0, 30)
    c["required_rr"]   = c["required_rr"].clip(0, 30)
    c["rrr_minus_crr"] = c["rrr_minus_crr"].clip(-30, 30)
    c = c[(c["balls_remaining"] >= 0) & (c["runs_needed"] >= 0)].copy()

    X = wp_pkl["scaler"].transform(c[FEATURES].fillna(0))
    raw = wp_pkl["model"].predict_proba(X)[:, 1]
    cal = wp_pkl["iso"].predict(raw) if "iso" in wp_pkl else raw
    c["wp"] = cal
    c["ball_num"] = 120 - c["balls_left"]
    return c

# ---------------- sidebar ----------------
st.sidebar.title("🏏 IPL Analytics")
page = st.sidebar.radio("Page", [
    "Overview", "Player Profile", "Team Comparison", "Venue Insights",
    "Matchup Explorer", "Auction Value", "Win Probability",
])

# ==================== PAGE 1: Overview ====================
if page == "Overview":
    st.title("Overview — IPL season trends")
    d = load_deliveries()
    first = (d[d["innings"] == 1]
             .groupby(["match_id", "season_year"], as_index=False)
             .agg(runs=("total_runs", "sum")))
    trend = first.groupby("season_year", as_index=False)["runs"].mean()

    col1, col2 = st.columns([2, 1])
    with col1:
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(trend["season_year"], trend["runs"], "o-", color="#1f77b4", lw=2)
        ax.set_xlabel("Season"); ax.set_ylabel("Avg 1st-innings score")
        ax.set_title("Average first-innings score by season")
        ax.grid(alpha=0.3)
        st.pyplot(fig)
    with col2:
        st.metric("Matches", f"{d['match_id'].nunique():,}")
        st.metric("Seasons", f"{d['season_year'].min()}–{d['season_year'].max()}")
        st.metric("Deliveries", f"{len(d):,}")

    st.subheader("Toss impact")
    m = load_matches().dropna(subset=["toss_winner", "winner"])
    m["toss_win"] = (m["toss_winner"] == m["winner"])
    rate = m["toss_win"].mean()
    c1, c2, c3 = st.columns(3)
    c1.metric("Toss winner also won match", f"{rate:.1%}")
    c2.metric("Field first (chose)", f"{(m['toss_decision']=='field').mean():.1%}")
    c3.metric("Bat first (chose)",   f"{(m['toss_decision']=='bat').mean():.1%}")

# ==================== PAGE 2: Player Profile ====================
elif page == "Player Profile":
    st.title("Player Profile")
    bat = load_batting(); bowl = load_bowling()
    all_players = sorted(set(bat["striker"]).union(set(bowl["bowler"])))
    player = st.selectbox("Select a player", all_players)

    bp = bat[bat["striker"] == player]
    wp = bowl[bowl["bowler"] == player]

    if not bp.empty:
        r = bp.iloc[0]
        st.subheader(f"🏏 Batting — {player} ({r['role']})")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Innings", int(r["innings"]))
        c2.metric("Runs",   int(r["runs"]))
        c3.metric("Avg",    f"{r['average']:.1f}" if pd.notna(r["average"]) else "—")
        c4.metric("SR",     f"{r['strike_rate']:.1f}")

        phases = ["Powerplay", "Middle", "Death"]
        srs = [r.get(f"SR_{p}") for p in phases]
        fig, ax = plt.subplots(figsize=(8, 3.5))
        bars = ax.bar(phases, [s if pd.notna(s) else 0 for s in srs],
                      color=["#4c72b0", "#dd8452", "#c44e52"])
        ax.set_ylabel("Strike rate"); ax.set_title(f"{player} — strike rate by phase")
        ax.grid(alpha=0.3, axis="y")
        for b, s in zip(bars, srs):
            if pd.notna(s):
                ax.text(b.get_x() + b.get_width()/2, s + 2, f"{s:.0f}", ha="center")
        st.pyplot(fig)

    if not wp.empty:
        r = wp.iloc[0]
        st.subheader(f"🎯 Bowling — {player}")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Innings", int(r["innings"]))
        c2.metric("Wickets", int(r["wickets"]))
        c3.metric("Economy", f"{r['economy']:.2f}")
        c4.metric("Bowling SR", f"{r['bowl_sr']:.1f}" if pd.notna(r["bowl_sr"]) else "—")

# ==================== PAGE 3: Team Comparison ====================
elif page == "Team Comparison":
    st.title("Team Comparison")
    m = load_matches().dropna(subset=["winner"]).copy()
    teams = sorted(set(m["team1"]).union(set(m["team2"])))
    c1, c2 = st.columns(2)
    t1 = c1.selectbox("Team A", teams, index=0)
    t2 = c2.selectbox("Team B", teams, index=1)

    h2h = m[((m["team1"] == t1) & (m["team2"] == t2)) |
            ((m["team1"] == t2) & (m["team2"] == t1))]
    if h2h.empty:
        st.warning("These two teams have never played.")
    else:
        w1 = (h2h["winner"] == t1).sum()
        w2 = (h2h["winner"] == t2).sum()
        st.metric("Matches played", len(h2h))
        c1, c2 = st.columns(2)
        c1.metric(f"{t1} wins", int(w1))
        c2.metric(f"{t2} wins", int(w2))

        fig, ax = plt.subplots(figsize=(8, 3.5))
        ax.bar([t1, t2], [w1, w2], color=["#4c72b0", "#c44e52"])
        ax.set_ylabel("Wins"); ax.set_title(f"Head-to-head: {t1} vs {t2}")
        for i, v in enumerate([w1, w2]):
            ax.text(i, v + 0.3, str(int(v)), ha="center", fontweight="bold")
        ax.grid(alpha=0.3, axis="y")
        st.pyplot(fig)

# ==================== PAGE 4: Venue Insights ====================
elif page == "Venue Insights":
    st.title("Venue Insights")
    d = load_deliveries(); m = load_matches()
    first = (d[d["innings"] == 1]
             .groupby(["match_id", "venue"], as_index=False)
             .agg(runs=("total_runs", "sum")))
    second = (d[d["innings"] == 2]
              .groupby(["match_id", "venue"], as_index=False)
              .agg(runs=("total_runs", "sum")))
    second = second.merge(m[["match_id", "winner"]], on="match_id", how="left")
    batting_second = (d[d["innings"] == 2]
                      .drop_duplicates("match_id")[["match_id", "batting_team"]])
    second = second.merge(batting_second, on="match_id", how="left")
    second["chase_won"] = (second["batting_team"] == second["winner"]).astype(int)

    vp = (first.groupby("venue")
          .agg(matches=("match_id", "count"), avg_first=("runs", "mean"))
          .join(second.groupby("venue")["chase_won"].mean().rename("chase_rate"), how="outer")
          .query("matches >= 20")
          .sort_values("matches", ascending=False)
          .round(2))
    st.dataframe(vp, use_container_width=True)

    fig, ax = plt.subplots(figsize=(11, 5))
    ax.scatter(vp["avg_first"], vp["chase_rate"], s=vp["matches"]*3,
               alpha=0.6, color="#4c72b0")
    for v, r in vp.iterrows():
        ax.annotate(v[:18], (r["avg_first"], r["chase_rate"]), fontsize=7)
    ax.axhline(0.5, ls="--", color="k", alpha=0.4)
    ax.set_xlabel("Avg first-innings score"); ax.set_ylabel("Chase win rate")
    ax.set_title("Venue profile (dot size = matches)")
    ax.grid(alpha=0.3)
    st.pyplot(fig)

# ==================== PAGE 5: Matchup Explorer ====================
elif page == "Matchup Explorer":
    st.title("Matchup Explorer")
    mu = load_matchups()
    if mu is None:
        st.warning("Run `05_matchups.ipynb` and save `matchups.csv` first.")
    else:
        c1, c2 = st.columns(2)
        batter = c1.selectbox("Batter", sorted(mu["striker"].unique()))
        bowlers = sorted(mu[mu["striker"] == batter]["bowler"].unique())
        bowler = c2.selectbox("Bowler", bowlers)

        row = mu[(mu["striker"] == batter) & (mu["bowler"] == bowler)]
        if row.empty:
            st.info("No qualifying matchup (min 20 balls).")
        else:
            r = row.iloc[0]
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Balls", int(r["balls_faced"]))
            c2.metric("Runs", int(r["runs"]))
            c3.metric("Dismissals", int(r["dismissals"]))
            c4.metric("SR", f"{r['SR']:.1f}")

            # All bowlers vs this batter
            st.subheader(f"{batter} vs all bowlers")
            sub = mu[mu["striker"] == batter].sort_values("balls_faced", ascending=False).head(15)
            fig, ax = plt.subplots(figsize=(10, 4))
            ax.barh(sub["bowler"], sub["SR"], color="#4c72b0")
            ax.axvline(130, ls="--", color="k", alpha=0.4)
            ax.invert_yaxis()
            ax.set_xlabel("Strike rate"); ax.set_title(f"{batter} — SR vs bowlers")
            ax.grid(alpha=0.3, axis="x")
            st.pyplot(fig)

# ==================== PAGE 6: Auction Value ====================
elif page == "Auction Value":
    st.title("Auction Value — player impact ranking")
    imp = load_impact()
    top_n = st.slider("Show top N", 10, 100, 30)

    st.subheader(f"Top {top_n} players by combined impact")
    st.dataframe(
        imp.head(top_n)[["rank", "player", "batting_impact", "bowling_impact",
                         "combined_impact", "role"]].round(2),
        use_container_width=True,
    )

    fig, ax = plt.subplots(figsize=(11, 5))
    t = imp.head(top_n)
    ax.barh(t["player"], t["combined_impact"], color="#55a868")
    ax.invert_yaxis()
    ax.set_xlabel("Combined impact score"); ax.set_title(f"Top {top_n} IPL players by impact")
    ax.grid(alpha=0.3, axis="x")
    st.pyplot(fig)

# ==================== PAGE 7: Win Probability ====================
elif page == "Win Probability":
    st.title("Ball-by-ball Win Probability")
    st.caption("Model: Logistic Regression · ROC-AUC 0.908 on 2024–2025 holdout")

    m = load_matches().dropna(subset=["winner"]).copy()
    m["label"] = (m["team1"] + " vs " + m["team2"] + " · " +
                  m["date"].astype(str) + " · " + m["match_id"])
    choice = st.selectbox("Pick a match", m["label"].tolist())
    match_id = choice.split(" · ")[-1].strip()

    c = compute_wp_curve(match_id)
    if c is None:
        st.error("Match not found in deliveries.")
    else:
        # Summary metrics at key points
        end = c.iloc[-1]
        mid = c.iloc[len(c)//2]
        c1, c2, c3 = st.columns(3)
        c1.metric("Chasing team", end["batting_team"])
        c2.metric("Final chase WP", f"{end['wp']:.1%}")
        c3.metric("Result", "WON" if end["wp"] > 0.5 else "LOST")

        # Plot
        fig, ax = plt.subplots(figsize=(13, 5))
        ax.axhspan(0, 0.5, alpha=0.08, color="red")
        ax.axhspan(0.5, 1, alpha=0.08, color="green")
        ax.plot(c["ball_num"], c["wp"], color="#1f77b4", lw=2,
                label="Chase win probability")
        wkts = c[c["is_wicket"] == 1]
        ax.scatter(wkts["ball_num"], wkts["wp"], color="red", s=60,
                   marker="v", zorder=3, label="Wicket")
        ax.axhline(0.5, color="k", ls="--", lw=0.8, alpha=0.5)
        ax.set_xlabel("Ball of the chase")
        ax.set_ylabel("Chasing team win probability")
        ax.set_ylim(0, 1)
        ax.set_title(f"Win probability — {match_id}")
        ax.legend(loc="best")
        ax.grid(alpha=0.3)
        st.pyplot(fig)

        with st.expander("Show ball-by-ball table"):
            cols = ["over", "ball", "batting_team", "runs_so_far",
                    "runs_needed", "balls_left", "wickets_left", "wp"]
            st.dataframe(c[cols].round(3), use_container_width=True)

# ---------------- footer ----------------
st.sidebar.markdown("---")
st.sidebar.caption("Built on Cricsheet ball-by-ball data · 2008–2025")