"use client";

import { useCallback, useEffect, useState } from "react";
import { AlertCircle, CalendarDays, Clock3, RefreshCw, Search, Trophy } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type Result = {
  match_id: string | number;
  season: string | number;
  date: string;
  venue?: string;
  team1: string;
  team2: string;
  winner?: string | null;
  result?: string;
  player_of_match?: string | null;
};
type LiveMatch = {
  match: string;
  name?: string;
  competition?: string;
  format?: string;
  state?: string;
  status?: string;
  starts_at?: string;
  venue?: string;
  teams?: { name: string; score?: string }[];
};

function dateLabel(value?: string) {
  if (!value) return "Date unavailable";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}

export default function LiveCentre() {
  const [tab, setTab] = useState<"live" | "upcoming" | "finished">("live");
  const [liveMatches, setLiveMatches] = useState<LiveMatch[]>([]);
  const [results, setResults] = useState<Result[]>([]);
  const [configured, setConfigured] = useState(false);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [season, setSeason] = useState("All");
  const [resultSearch, setResultSearch] = useState("");
  const [lastUpdated, setLastUpdated] = useState("");

  const load = useCallback(async (quiet = false) => {
    if (quiet) setRefreshing(true);
    else setLoading(true);
    setError("");
    try {
      if (tab === "finished") {
        const response = await fetch(API + "/api/results?limit=100", { cache: "no-store" });
        const body = await response.json();
        if (!response.ok) throw new Error(body.detail || "Could not load historical results.");
        setResults(body);
      } else {
        const statusResponse = await fetch(API + "/api/live/status", { cache: "no-store" });
        const status = await statusResponse.json();
        setConfigured(Boolean(status.configured));
        if (!status.configured) {
          setLiveMatches([]);
          setError("Live fixtures are not connected. The historical results archive is available in the Results tab.");
          return;
        }
        const response = await fetch(API + "/api/live/matches?state=" + tab, { cache: "no-store" });
        const body = await response.json();
        if (!response.ok) throw new Error(body.detail || "This fixture feed is not available on the current provider plan.");
        setLiveMatches(body?.data?.results || []);
      }
      setLastUpdated(new Date().toISOString());
    } catch (e: any) {
      setError(e?.message || "Unable to load match information.");
      if (tab === "finished") setResults([]);
      else setLiveMatches([]);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [tab]);

  useEffect(() => { load(); }, [load]);
  const seasons = Array.from(new Set(results.map(row => String(row.season)))).sort((a, b) => Number(b) - Number(a));
  const visibleResults = results.filter(row => {
    const matchesSeason = season === "All" || String(row.season) === season;
    const q = resultSearch.trim().toLowerCase();
    const matchesQuery = !q || [row.team1, row.team2, row.winner, row.player_of_match, row.venue, row.result]
      .some(value => String(value || "").toLowerCase().includes(q));
    return matchesSeason && matchesQuery;
  });

  return <section className="live-centre">
    <div className="match-centre-heading">
      <div>
        <div className="match-breadcrumb">IPL MATCH CENTRE <span>/</span> {tab === "finished" ? "RESULTS" : tab.toUpperCase()}</div>
        <h1>Match Centre</h1>
        <p>Fixtures, live coverage and completed IPL match records.</p>
      </div>
      <div className="archive-note"><Trophy size={16}/> Historical IPL archive</div>
    </div>

    <div className="live-toolbar">
      <div className="live-tabs" role="tablist" aria-label="Match category">
        {(["live", "upcoming", "finished"] as const).map(item =>
          <button key={item} role="tab" aria-selected={tab === item}
            className={tab === item ? "live-tab active" : "live-tab"}
            onClick={() => { setTab(item); setError(""); }}>
            {item === "finished" ? "Results" : item === "upcoming" ? "Upcoming" : "Live"}
          </button>
        )}
      </div>
      <button className="refresh-button" onClick={() => load(true)} disabled={refreshing}>
        <RefreshCw size={14} className={refreshing ? "refresh-spin" : ""}/> Refresh
      </button>
    </div>

    {tab === "finished" ? <>
      <div className="results-toolbar">
        <div><span className="match-section-label">COMPLETED MATCHES</span><h2>IPL results archive</h2></div>
        <div className="results-controls">
          <label className="results-search"><Search size={14}/><input value={resultSearch} onChange={e => setResultSearch(e.target.value)} placeholder="Search teams, players or venue" aria-label="Search results"/></label>
          <label className="results-season">Season
            <select value={season} onChange={e => setSeason(e.target.value)}>
              <option value="All">All seasons</option>
              {seasons.map(value => <option key={value} value={value}>{value}</option>)}
            </select>
          </label>
          <span className="results-count">{visibleResults.length} matches</span>
        </div>
      </div>
      {error && <div className="match-info"><AlertCircle size={16}/>{error}</div>}
      {loading ? <div className="match-loading">Loading match results…</div> :
        <div className="results-table-wrap">
          <table className="results-table">
            <thead><tr><th>DATE</th><th>MATCH</th><th>WINNER</th><th>RESULT</th><th>PLAYER OF THE MATCH</th><th>VENUE</th></tr></thead>
            <tbody>
              {visibleResults.map(row => <tr key={row.match_id}>
                <td><span className="result-date">{dateLabel(row.date)}</span><small>{row.season}</small></td>
                <td><b>{row.team1}</b><span className="versus-label">vs</span><b>{row.team2}</b></td>
                <td>{row.winner ? <span className="winner-label">{row.winner}</span> : "No result"}</td>
                <td>{row.result || "Result unavailable"}</td>
                <td>{row.player_of_match || "—"}</td>
                <td>{row.venue || "—"}</td>
              </tr>)}
            </tbody>
          </table>
          {!visibleResults.length && <div className="match-loading">No results found for this season.</div>}
        </div>
      }
      <p className="data-footnote">Results are from the project's processed historical IPL dataset. Ball-by-ball scorecards are not included in this archive view.</p>
    </> : <>
      <div className="results-toolbar">
        <div><span className="match-section-label">{tab === "live" ? "LIVE COVERAGE" : "FIXTURE LIST"}</span>
          <h2>{tab === "live" ? "Matches in progress" : "Upcoming fixtures"}</h2></div>
        <span className="updated-label">{lastUpdated ? "Checked " + new Date(lastUpdated).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" }) : "Provider feed"}</span>
      </div>
      {error && <div className="match-info"><AlertCircle size={16}/><span>{error}</span></div>}
      {loading ? <div className="match-loading">Checking the cricket data provider…</div> :
        liveMatches.length ? <div className="provider-match-list">{liveMatches.map(match =>
          <article className="provider-match-row" key={match.match}>
            <div><span className="match-section-label">{match.competition || "CRICKET"}</span><h3>{match.name || match.match}</h3>
              <small>{match.format || "Match"} · {match.venue || "Venue unavailable"}</small></div>
            <div className="provider-match-teams">{(match.teams || []).slice(0, 2).map(team =>
              <div key={team.name}><b>{team.name}</b><strong>{team.score || "—"}</strong></div>)}</div>
            <span className="provider-match-status">{match.status || match.state || dateLabel(match.starts_at)}</span>
          </article>)}</div> :
          !error && <div className="match-loading">No matches are currently listed in this category.</div>
      }
      <p className="data-footnote">Live and fixture listings depend on the connected provider's plan and feed availability. No scores or fixtures are simulated.</p>
    </>}
    <div className="match-centre-footer"><span><Clock3 size={13}/> Data checked from the configured source</span><span>IPL INTELLIGENCE</span></div>
  </section>;
}
