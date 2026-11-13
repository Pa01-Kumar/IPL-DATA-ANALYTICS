"use client";

import { useCallback, useEffect, useState } from "react";
import { AlertCircle, Award, CalendarDays, Clock3, MapPin, RefreshCw, Search, Trophy, X } from "lucide-react";

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
type ScorecardInnings = { innings: number; batting_team: string; bowling_team: string; runs: number; wickets: number; overs: string; run_rate: number; extras: number; batting: { player: string; runs: number; balls: number; fours: number; sixes: number; strike_rate: number; dismissal: string }[]; bowling: { player: string; overs: string; maidens: number; runs: number; wickets: number; economy: number }[]; fall_of_wickets: { wicket: number; score: number; overs: string; player: string; type: string }[]; over_summary: { over: number; runs: number; wickets: number; balls: number }[] };
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
  const [resultsPage, setResultsPage] = useState(1);
  const [selectedMatch, setSelectedMatch] = useState<Result | null>(null);
  const [scorecard, setScorecard] = useState<ScorecardInnings[]>([]);
  const [scorecardLoading, setScorecardLoading] = useState(false);
  const [scorecardError, setScorecardError] = useState("");
  const pageSize = 15;

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
  const pageCount = Math.max(1, Math.ceil(visibleResults.length / pageSize));
  const pageResults = visibleResults.slice((resultsPage - 1) * pageSize, resultsPage * pageSize);
  const pageStart = visibleResults.length ? (resultsPage - 1) * pageSize + 1 : 0;
  const pageEnd = Math.min(resultsPage * pageSize, visibleResults.length);

  useEffect(() => { setResultsPage(1); }, [resultSearch, season]);
  useEffect(() => {
    if (!selectedMatch) { setScorecard([]); setScorecardError(""); return; }
    const controller = new AbortController();
    setScorecardLoading(true); setScorecardError(""); setScorecard([]);
    fetch(API + "/api/results/" + encodeURIComponent(String(selectedMatch.match_id)) + "/scorecard", { cache: "no-store", signal: controller.signal })
      .then(async response => { const body = await response.json(); if (!response.ok) throw new Error(body.detail || "Scorecard unavailable."); return body; })
      .then(body => setScorecard(body.innings || []))
      .catch(error => { if (error.name !== "AbortError") setScorecardError(error.message || "Unable to load scorecard."); })
      .finally(() => { if (!controller.signal.aborted) setScorecardLoading(false); });
    return () => controller.abort();
  }, [selectedMatch]);
  useEffect(() => { if (!selectedMatch) return;
    const onKeyDown = (event: KeyboardEvent) => { if (event.key === "Escape") setSelectedMatch(null); };
    document.addEventListener("keydown", onKeyDown); document.body.style.overflow = "hidden";
    return () => { document.removeEventListener("keydown", onKeyDown); document.body.style.overflow = ""; };
  }, [selectedMatch]);

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
          <span className="results-count">{pageStart}–{pageEnd} of {visibleResults.length}</span>
          {(resultSearch || season !== "All") && <button className="results-clear" onClick={() => { setResultSearch(""); setSeason("All"); }}>Clear filters</button>}
        </div>
      </div>
      <div className="results-summary" aria-label="Results archive summary">
        <div className="results-summary-card"><span>ARCHIVE RECORDS</span><strong>{results.length.toLocaleString("en-IN")}</strong><small>Loaded from historical dataset</small></div>
        <div className="results-summary-card"><span>SEASONS COVERED</span><strong>{seasons.length}</strong><small>{seasons.length ? seasons[seasons.length - 1] + " – " + seasons[0] : "No season data"}</small></div>
        <div className="results-summary-card"><span>TEAMS FEATURED</span><strong>{new Set(results.flatMap(row => [row.team1, row.team2])).size}</strong><small>Distinct franchises in this result set</small></div>
        <div className="results-summary-card results-summary-highlight"><span>CURRENT VIEW</span><strong>{visibleResults.length.toLocaleString("en-IN")}</strong><small>Matches after search and season filters</small></div>
      </div>
      {error && <div className="match-info"><AlertCircle size={16}/>{error}</div>}
      {loading ? <div className="match-loading">Loading match results…</div> :
        <div className="results-table-wrap">
          <table className="results-table">
            <thead><tr><th>DATE</th><th>MATCH</th><th>WINNER</th><th>RESULT</th><th>PLAYER OF THE MATCH</th><th>VENUE</th></tr></thead>
            <tbody>
              {pageResults.map(row => <tr key={row.match_id} className="result-match-row" tabIndex={0} role="button" aria-label={"View details for " + row.team1 + " versus " + row.team2} onClick={() => setSelectedMatch(row)} onKeyDown={event => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); setSelectedMatch(row); } }}>
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
      {!loading && visibleResults.length > pageSize && <nav className="results-pagination" aria-label="Results pages">
        <span>Showing <b>{pageStart}–{pageEnd}</b> of <b>{visibleResults.length}</b> matches</span>
        <div>
          <button type="button" onClick={() => setResultsPage(value => Math.max(1, value - 1))} disabled={resultsPage === 1}>Previous</button>
          <span>Page <b>{resultsPage}</b> of <b>{pageCount}</b></span>
          <button type="button" onClick={() => setResultsPage(value => Math.min(pageCount, value + 1))} disabled={resultsPage === pageCount}>Next</button>
        </div>
      </nav>}
      <p className="data-footnote">Select any match to open its details. Results are from the processed historical IPL dataset.</p>
{selectedMatch && <div className="match-detail-backdrop" onMouseDown={event => { if (event.target === event.currentTarget) setSelectedMatch(null); }}>
<section className="match-detail-modal" role="dialog" aria-modal="true" aria-labelledby="match-detail-title">
<header className="match-detail-top"><div><span className="match-section-label">MATCH DETAILS · IPL {selectedMatch.season}</span><h2 id="match-detail-title">{selectedMatch.team1} <span>vs</span> {selectedMatch.team2}</h2></div><button type="button" className="match-detail-close" onClick={() => setSelectedMatch(null)} aria-label="Close match details"><X size={18}/></button></header>
<div className="match-detail-result"><span className="match-detail-status"><Trophy size={14}/> COMPLETED</span><strong>{selectedMatch.winner || "Match ended without a winner"}</strong><p>{selectedMatch.result || "Final result details unavailable"}</p></div>
<div className="match-detail-facts">
<div><CalendarDays size={15}/><span><small>DATE</small><b>{dateLabel(selectedMatch.date)}</b></span></div>
<div><MapPin size={15}/><span><small>VENUE</small><b>{selectedMatch.venue || "Not available"}</b></span></div>
<div><Award size={15}/><span><small>PLAYER OF THE MATCH</small><b>{selectedMatch.player_of_match || "Not recorded"}</b></span></div>
<div><Trophy size={15}/><span><small>MATCH ID</small><b>#{selectedMatch.match_id}</b></span></div></div>
<div className="match-detail-scorecard"><div><h3>Scorecard</h3><span>Historical ball-by-ball archive</span></div>
{scorecardLoading ? <p>Loading innings scorecard…</p> : scorecardError ? <p>{scorecardError}</p> : !scorecard.length ? <p>No delivery scorecard is available for this match.</p> :
scorecard.map(inn => <div className="scorecard-innings" key={inn.innings}>
<div className="scorecard-innings-heading"><strong>{inn.batting_team}</strong><b>{inn.runs}/{inn.wickets}</b><span>{inn.overs} overs · RR {inn.run_rate}</span></div>
<div className="scorecard-columns">
<section className="scorecard-panel"><h4>Batting</h4><div className="scorecard-table-scroll"><table className="scorecard-table"><thead><tr><th>Batter</th><th>R</th><th>B</th><th>4s</th><th>6s</th><th>SR</th></tr></thead><tbody>{inn.batting.map(p => <tr key={p.player}><td><b>{p.player}</b><small>{p.dismissal}</small></td><td>{p.runs}</td><td>{p.balls}</td><td>{p.fours}</td><td>{p.sixes}</td><td>{p.strike_rate}</td></tr>)}</tbody></table></div><p className="scorecard-extras">Extras: {inn.extras} <span>·</span> Total: {inn.runs}/{inn.wickets}</p></section>
<section className="scorecard-panel"><h4>Bowling</h4><div className="scorecard-table-scroll"><table className="scorecard-table"><thead><tr><th>Bowler</th><th>O</th><th>M</th><th>R</th><th>W</th><th>Eco</th></tr></thead><tbody>{inn.bowling.map(p => <tr key={p.player}><td><b>{p.player}</b></td><td>{p.overs}</td><td>{p.maidens}</td><td>{p.runs}</td><td>{p.wickets}</td><td>{p.economy}</td></tr>)}</tbody></table></div></section>
</div>
<div className="scorecard-bottom-grid">
<section className="scorecard-panel"><h4>Fall of wickets</h4><div className="scorecard-fow-list">{inn.fall_of_wickets.length ? inn.fall_of_wickets.map(w => <span key={w.wicket}><b>{w.wicket}-{w.score}</b><small>{w.player} · {w.overs} ov</small></span>) : <p>No wickets recorded.</p>}</div></section>
<section className="scorecard-panel"><h4>Over-by-over</h4><div className="scorecard-over-list">{inn.over_summary.map(o => <span key={o.over}><b>{o.over}</b><strong>{o.runs}{o.wickets ? `/${o.wickets}` : ""}</strong></span>)}</div></section>
</div>/div>
</div>)}</div>
<footer className="match-detail-footer"><span>Source: processed IPL historical records</span><button type="button" onClick={() => setSelectedMatch(null)}>Back to results</button></footer></section></div>}
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
