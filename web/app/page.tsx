"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Activity, ArrowDownRight, ArrowUpRight, BarChart3, ChevronDown, CircleHelp,
  Command, Compass, Crosshair, Gauge, LayoutDashboard, Menu, Search, Shield,
  SlidersHorizontal, Sparkles, Swords, Trophy, Users, X
} from "lucide-react";
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer,
  Tooltip, XAxis, YAxis
} from "recharts";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
type PageKey = "Overview" | "Players" | "Teams" | "Venues" | "Matchups" | "Impact" | "Win Probability" | "Franchise Fit";
type AnyRow = Record<string, any>;
const nav: { label: PageKey; icon: any; group: string }[] = [
  { label: "Overview", icon: LayoutDashboard, group: "WORKSPACE" },
  { label: "Players", icon: Users, group: "WORKSPACE" },
  { label: "Teams", icon: Shield, group: "WORKSPACE" },
  { label: "Venues", icon: Compass, group: "WORKSPACE" },
  { label: "Matchups", icon: Swords, group: "WORKSPACE" },
  { label: "Impact", icon: Activity, group: "INTELLIGENCE" },
  { label: "Win Probability", icon: Gauge, group: "INTELLIGENCE" },
  { label: "Franchise Fit", icon: Crosshair, group: "INTELLIGENCE" },
];

async function get<T,>(path: string): Promise<T> {
  const res = await fetch(API + path, { cache: "no-store" });
  if (!res.ok) throw new Error("API request failed");
  return res.json();
}
const fmt = (n: number) => new Intl.NumberFormat("en-IN").format(n || 0);
const num = (n: any, d = 1) => Number(n || 0).toFixed(d);

function Metric({ label, value, note, icon: Icon }: { label: string; value: string; note: string; icon: any }) {
  return <article className="metric-card"><div className="metric-top"><span>{label}</span><span className="metric-icon"><Icon size={17}/></span></div><strong>{value}</strong><small>{note}</small></article>;
}
function SectionTitle({ eyebrow, title, detail }: { eyebrow: string; title: string; detail: string }) {
  return <div className="section-title"><div><span className="eyebrow">{eyebrow}</span><h2>{title}</h2><p>{detail}</p></div></div>;
}

export default function Home() {
  const [page, setPage] = useState<PageKey>("Overview");
  const [overview, setOverview] = useState<AnyRow | null>(null);
  const [players, setPlayers] = useState<AnyRow[]>([]);
  const [teams, setTeams] = useState<AnyRow[]>([]);
  const [venues, setVenues] = useState<AnyRow[]>([]);
  const [shortlist, setShortlist] = useState<AnyRow[]>([]);
  const [search, setSearch] = useState("");
  const [role, setRole] = useState("All");
  const [teamA, setTeamA] = useState("");
  const [teamB, setTeamB] = useState("");
  const [comparison, setComparison] = useState<AnyRow | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [mobileNav, setMobileNav] = useState(false);
  const [selectedPlayer, setSelectedPlayer] = useState<AnyRow | null>(null);
  async function openPlayer(name: string) {
    try {
      setSelectedPlayer(await get<AnyRow>("/api/players/" + encodeURIComponent(name)));
    } catch {
      setError("Could not load the selected player profile.");
    }
  }

  useEffect(() => {
    Promise.all([
      get<AnyRow>("/api/overview"), get<AnyRow[]>("/api/players?limit=200"),
      get<AnyRow[]>("/api/teams"), get<AnyRow[]>("/api/venues"),
      get<AnyRow[]>("/api/shortlist?limit=12")
    ]).then(([o,p,t,v,s]) => {
      setOverview(o); setPlayers(p); setTeams(t); setVenues(v); setShortlist(s);
      setTeamA(t[0]?.team || ""); setTeamB(t[1]?.team || "");
    }).catch(() => setError("Can't connect to the analytics API. Start the FastAPI server on port 8000."))
      .finally(() => setLoading(false));
  }, []);

  const filteredPlayers = useMemo(() => players.filter(p =>
    String(p.player).toLowerCase().includes(search.toLowerCase()) &&
    (role === "All" || String(p.role).toLowerCase().includes(role.toLowerCase()))
  ), [players, search, role]);

  async function compare() {
    if (!teamA || !teamB) return;
    try { setComparison(await get<AnyRow>(`/api/teams/compare?team_a=${encodeURIComponent(teamA)}&team_b=${encodeURIComponent(teamB)}`)); }
    catch { setError("Unable to compare those teams."); }
  }

  return <main className="app-shell">
    <aside className={`sidebar ${mobileNav ? "sidebar-open" : ""}`}>
      <div className="brand"><div className="brand-mark">✦</div><div><b>IPL<span>INTELLIGENCE</span></b><small>CRICKET, DECODED.</small></div><button className="mobile-close" onClick={() => setMobileNav(false)}><X/></button></div>
      <div className="workspace-label">PLATFORM</div>
      {["WORKSPACE", "INTELLIGENCE"].map(group => <div className="nav-group" key={group}><p>{group}</p>{nav.filter(n => n.group === group).map(item => {
        const Icon = item.icon; return <button key={item.label} className={page === item.label ? "nav-item active" : "nav-item"} onClick={() => {setPage(item.label);setMobileNav(false);}}><Icon size={18}/><span>{item.label}</span>{page === item.label && <i/>}</button>;
      })}</div>)}
      <div className="sidebar-bottom"><div className="live-dot"/> HISTORICAL DATA ENGINE <small>Cricsheet · Processed IPL archive</small></div>
    </aside>

    <section className="main-area">
      <header className="topbar"><button className="mobile-menu" onClick={() => setMobileNav(true)}><Menu/></button><div className="breadcrumb">IPL INTELLIGENCE <span>/</span> {page.toUpperCase()}</div><div className="top-actions"><span className="status"><i/> DATA ENGINE</span><div className="avatar">PK</div></div></header>
      <div className="content">
        {error && <div className="error-banner">{error}</div>}
        {loading ? <div className="loading"><div className="loader"/><span>Loading cricket intelligence…</span></div> : !overview ? <div className="empty-state">Analytics data could not be loaded.</div> : <>
          {page === "Overview" && <Overview data={overview}/>}
          {page === "Players" && <Players rows={filteredPlayers} search={search} setSearch={setSearch} role={role} setRole={setRole} onSelect={openPlayer}/>}
          {page === "Teams" && <Teams rows={teams} teamA={teamA} teamB={teamB} setTeamA={setTeamA} setTeamB={setTeamB} compare={compare} result={comparison}/>}
          {page === "Venues" && <Venues rows={venues}/>}
          {page === "Matchups" && <Matchups/>}
          {page === "Impact" && <Players rows={players} search={search} setSearch={setSearch} role={role} setRole={setRole} impact onSelect={openPlayer}/>}
          {page === "Win Probability" && <WinProbability/>}
          {page === "Franchise Fit" && <Shortlist rows={shortlist}/>}\n          {selectedPlayer && <PlayerModal player={selectedPlayer} onClose={() => setSelectedPlayer(null)}/>}
        </>}
        <footer className="footer"><span>IPL INTELLIGENCE © 2026</span><span>BUILT ON HISTORICAL CRICSHEET DATA · NOT A LIVE FEED</span></footer>
      </div>
    </section>
  </main>;
}

function Overview({data}: {data: AnyRow}) {
  const s=data.summary;
  return <><div className="hero"><div className="hero-copy"><span className="eyebrow"><Sparkles size={13}/> THE IPL DATA ROOM</span><h1>See the game<br/><em>before it unfolds.</em></h1><p>Performance intelligence, player discovery and franchise strategy — all in one place.</p><div className="hero-meta"><span><i/> DATA THROUGH {s.lastSeason}</span><span>SEASONS {s.firstSeason}—{s.lastSeason}</span></div></div><div className="hero-art"><div className="orbit orbit-one"/><div className="orbit orbit-two"/><div className="cricket-ball">✦</div><div className="hero-art-label">MATCH<br/>INTELLIGENCE</div></div></div>
    <div className="metrics-grid"><Metric label="Matches analysed" value={fmt(s.matches)} note="Across the processed archive" icon={Trophy}/><Metric label="Seasons covered" value={fmt(s.seasons)} note={`${s.firstSeason} to ${s.lastSeason}`} icon={BarChart3}/><Metric label="Players indexed" value={fmt(s.players)} note="Batting, bowling & impact" icon={Users}/><Metric label="Teams tracked" value={fmt(s.teams)} note="Historical franchise records" icon={Shield}/></div>
    <div className="dashboard-grid"><section className="panel panel-wide"><SectionTitle eyebrow="SEASON BY SEASON" title="Scoring landscape" detail="Matches recorded across each IPL season."/><div className="chart-wrap"><ResponsiveContainer width="100%" height={260}><AreaChart data={data.seasonTrend}><defs><linearGradient id="seasonFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#b7f36b" stopOpacity={0.28}/><stop offset="100%" stopColor="#b7f36b" stopOpacity={0}/></linearGradient></defs><CartesianGrid stroke="#263244" vertical={false}/><XAxis dataKey="season" stroke="#728096" tickLine={false} axisLine={false}/><YAxis stroke="#728096" tickLine={false} axisLine={false}/><Tooltip contentStyle={{background:"#111b2a",border:"1px solid #2c394c",borderRadius:12}}/><Area type="monotone" dataKey="matches" stroke="#b7f36b" strokeWidth={2.5} fill="url(#seasonFill)"/></AreaChart></ResponsiveContainer></div></section>
    <section className="panel"><SectionTitle eyebrow="MOST WINS" title="Franchise leaders" detail="Matches won in the dataset."/><div className="rank-list">{data.teamWins.slice(0,7).map((t:AnyRow,i:number)=><div className="rank-row" key={t.team}><span className="rank-number">{String(i+1).padStart(2,"0")}</span><span className="rank-name">{t.team}</span><b>{t.wins}</b></div>)}</div></section></div>
    <div className="dashboard-grid"><section className="panel"><SectionTitle eyebrow="RUN MACHINE" title="Top run scorers" detail="Career aggregate in the processed dataset."/><div className="player-mini-list">{data.topBatters.map((p:AnyRow,i:number)=><div className="player-mini" key={p.striker}><div className="player-initial">{p.striker.split(" ").map((x:string)=>x[0]).join("").slice(0,2)}</div><div className="player-mini-name"><b>{p.striker}</b><small>{p.innings} innings · avg {num(p.average)}</small></div><strong>{fmt(p.runs)}<small>RUNS</small></strong></div>)}</div></section>
    <section className="panel"><SectionTitle eyebrow="IMPACT INDEX" title="Top impact players" detail="Project-defined combined impact score."/><div className="impact-list">{data.topImpact.map((p:AnyRow,i:number)=><div className="impact-row" key={p.player}><span>{i+1}</span><div><b>{p.player}</b><small>{p.role}</small></div><strong>{num(p.combined_impact,2)}</strong></div>)}</div></section></div></>;
}

function Players({rows,search,setSearch,role,setRole,impact=false,onSelect}:{rows:AnyRow[];search:string;setSearch:(s:string)=>void;role:string;setRole:(s:string)=>void;impact?:boolean;onSelect:(name:string)=>void}) {
  return <><SectionTitle eyebrow={impact?"PLAYER PERFORMANCE INDEX":"PLAYER DIRECTORY"} title={impact?"Impact rankings":"Find your next match-winner"} detail={impact?"Compare the project's historical player impact scores.":"Explore player profiles through batting, bowling and combined performance."}/>
    <div className="toolbar"><div className="search-box"><Search size={17}/><input placeholder="Search player name…" value={search} onChange={e=>setSearch(e.target.value)}/></div><select value={role} onChange={e=>setRole(e.target.value)}><option>All</option><option>Batter</option><option>Bowler</option><option>All-rounder</option><option>Opener</option><option>Finisher</option></select><span className="result-count">{rows.length} PLAYERS</span></div>
    <div className="player-grid">{rows.slice(0,80).map((p,i)=><button type="button" className="player-card player-card-button" key={p.player} onClick={() => onSelect(p.player)}><div className="player-card-top"><span className="player-index">PLAYER / {String(i+1).padStart(2,"0")}</span><span className="role-pill">{p.role||"Player"}</span></div><div className="player-avatar">{String(p.player).split(" ").map((x:string)=>x[0]).join("").slice(0,2)}</div><h3>{p.player}</h3><div className="player-stat-grid"><div><b>{fmt(p.runs)}</b><small>RUNS</small></div><div><b>{num(p.average)}</b><small>AVERAGE</small></div><div><b>{num(p.strike_rate)}</b><small>STRIKE RATE</small></div></div><div className="player-card-foot"><span>IMPACT SCORE</span><b>{num(p.combined_impact,2)}</b></div></article>)}</div>
  </>;
}

function Teams({rows,teamA,teamB,setTeamA,setTeamB,compare,result}:{rows:AnyRow[];teamA:string;teamB:string;setTeamA:(s:string)=>void;setTeamB:(s:string)=>void;compare:()=>void;result:AnyRow|null}) {
  return <><SectionTitle eyebrow="FRANCHISE ANALYTICS" title="Rivalry, measured." detail="Compare historical head-to-head records between IPL teams."/><div className="compare-panel"><div className="team-select"><label>FRANCHISE A</label><select value={teamA} onChange={e=>setTeamA(e.target.value)}>{rows.map(t=><option key={t.team}>{t.team}</option>)}</select></div><div className="versus">VS</div><div className="team-select"><label>FRANCHISE B</label><select value={teamB} onChange={e=>setTeamB(e.target.value)}>{rows.map(t=><option key={t.team}>{t.team}</option>)}</select></div><button className="primary-button" onClick={compare}>Compare teams <ArrowUpRight size={16}/></button></div>
    {result&&<div className="panel comparison-result"><div className="compare-score"><div><small>{result.teamA}</small><strong>{result.winsA}</strong><span>WINS</span></div><div className="compare-mid"><b>{result.played}</b><small>MATCHES PLAYED</small></div><div><small>{result.teamB}</small><strong>{result.winsB}</strong><span>WINS</span></div></div><div className="versus-bar"><i style={{width:`${result.played?result.winsA/result.played*100:50}%`}}/></div></div>}
    <div className="team-grid">{rows.map((t,i)=><article className="team-card" key={t.team}><span>FRANCHISE / {String(i+1).padStart(2,"0")}</span><h3>{t.team}</h3><div className="team-numbers"><div><b>{t.played}</b><small>PLAYED</small></div><div><b>{t.wins}</b><small>WINS</small></div><div><b>{t.winRate}%</b><small>WIN RATE</small></div></div></article>)}</div>
  </>;
}

function Venues({rows}:{rows:AnyRow[]}) {
  return <><SectionTitle eyebrow="GROUND REPORT" title="Every venue has a story." detail="Explore the historical grounds represented in the match archive."/><div className="venue-grid">{rows.map((v,i)=><article className="venue-card" key={v.venue}><div className="venue-number">{String(i+1).padStart(2,"0")}</div><div><span>VENUE PROFILE</span><h3>{v.venue}</h3><p>{fmt(v.matches)} recorded matches</p></div><ArrowUpRight/></article>)}</div></>;
}

function Matchups() {
  const [batter,setBatter]=useState(""); const [bowler,setBowler]=useState(""); const [rows,setRows]=useState<AnyRow[]>([]);
  async function search(){try{setRows(await get<AnyRow[]>(`/api/matchups?batter=${encodeURIComponent(batter)}&bowler=${encodeURIComponent(bowler)}&limit=40`));}catch{}}
  return <><SectionTitle eyebrow="BATTLE ANALYSIS" title="Batter vs bowler." detail="Look beyond averages. Explore the individual contests inside the game."/><div className="toolbar"><div className="search-box"><Search size={16}/><input placeholder="Filter batter…" value={batter} onChange={e=>setBatter(e.target.value)}/></div><div className="search-box"><Crosshair size={16}/><input placeholder="Filter bowler…" value={bowler} onChange={e=>setBowler(e.target.value)}/></div><button className="primary-button" onClick={search}>Explore matchup</button></div><div className="panel table-panel"><div className="table-heading">MATCHUP RECORDS <span>{rows.length} RESULTS</span></div><div className="table-scroll"><table><thead><tr><th>BATTER</th><th>BOWLER</th><th>BALLS</th><th>RUNS</th><th>DISMISSALS</th><th>STRIKE RATE</th></tr></thead><tbody>{rows.map((r,i)=><tr key={i}><td>{r.striker}</td><td>{r.bowler}</td><td>{fmt(r.balls_faced)}</td><td>{fmt(r.runs)}</td><td>{fmt(r.dismissals)}</td><td>{num(r.SR)}</td></tr>)}</tbody></table></div></div></>;
}

function Shortlist({rows}:{rows:AnyRow[]}) {
  return <><SectionTitle eyebrow="SQUAD BUILDING LAB" title="Find the right fit." detail="A data-led shortlist shaped by role priorities and historical player impact."/><div className="notice"><CircleHelp size={17}/> Statistical shortlist based on historical performance. This is not an official team requirement or transfer recommendation.</div><div className="shortlist-grid">{rows.map((p,i)=><article className="shortlist-card" key={p.player}><div className="shortlist-rank">#{String(i+1).padStart(2,"0")} <span>{p.fit_category}</span></div><h3>{p.player}</h3><div className="fit-score"><strong>{num(p.franchise_fit_score*100,0)}</strong><span>FIT INDEX</span></div><div className="fit-meter"><i style={{width:`${Math.min(100,p.franchise_fit_score*100)}%`}}/></div><div className="fit-details"><span>Batting impact <b>{num(p.batting_impact)}</b></span><span>Bowling impact <b>{num(p.bowling_impact)}</b></span><span>Combined impact <b>{num(p.combined_impact)}</b></span></div></article>)}</div></>;
}

function WinProbability() {
  return <><SectionTitle eyebrow="MODEL CENTRE" title="Win probability." detail="Historical chase-state model. Interactive match replay will connect to the saved Logistic Regression artifact in the next integration pass."/><div className="model-placeholder"><Gauge size={34}/><h3>Historical match replay</h3><p>The existing model and ball-by-ball data are retained. The new match-centre visualisation is being connected to the Python inference layer.</p><span>MODEL ARTIFACT · winprob_logistic.pkl</span></div></>;
}

function PlayerModal({player,onClose}:{player:AnyRow;onClose:()=>void}) {
  return <div className="modal-backdrop" onClick={onClose}>
    <section className="modal-card" onClick={e=>e.stopPropagation()}>
      <button className="modal-close" onClick={onClose}><X size={18}/></button>
      <span className="eyebrow">PLAYER DOSSIER</span><h2>{player.player}</h2>
      <p className="modal-role">{player.role || "IPL Player"}</p>
      <div className="modal-stats">
        <div><b>{fmt(player.runs)}</b><small>RUNS</small></div>
        <div><b>{num(player.average)}</b><small>AVERAGE</small></div>
        <div><b>{num(player.strike_rate)}</b><small>STRIKE RATE</small></div>
        <div><b>{fmt(player.wickets)}</b><small>WICKETS</small></div>
        <div><b>{num(player.economy)}</b><small>ECONOMY</small></div>
        <div><b>{num(player.combined_impact)}</b><small>IMPACT</small></div>
      </div>
      <p className="modal-note">Historical career aggregates from the checked-in IPL dataset. Missing values are not estimated.</p>
    </section>
  </div>;
}

