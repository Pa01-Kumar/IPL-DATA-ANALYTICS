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
    <div className="player-grid">{rows.slice(0,80).map((p,i)=><button type="button" className="player-card player-card-button" key={p.player} onClick={() => onSelect(p.player)}><div className="player-card-top"><span className="player-index">PLAYER / {String(i+1).padStart(2,"0")}</span><span className="role-pill">{p.role||"Player"}</span></div><div className="player-avatar">{String(p.player).split(" ").map((x:string)=>x[0]).join("").slice(0,2)}</div><h3>{p.player}</h3><div className="player-stat-grid"><div><b>{fmt(p.runs)}</b><small>RUNS</small></div><div><b>{num(p.average)}</b><small>AVERAGE</small></div><div><b>{num(p.strike_rate)}</b><small>STRIKE RATE</small></div></div><div className="player-card-foot"><span>IMPACT SCORE</span><b>{num(p.combined_impact,2)}</b></div></button>)}</div>
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
  const [bat,setBat]=useState(0.8),[bowl,setBowl]=useState(0.8),[all,setAll]=useState(1);
  const [roles,setRoles]=useState(["Batter","Bowler","All-rounder"]),[limit,setLimit]=useState(15);
  const [items,setItems]=useState(rows),[busy,setBusy]=useState(false);
  async function refresh() {
    setBusy(true);
    try {
      const q="?batting_priority="+bat+"&bowling_priority="+bowl+"&allrounder_priority="+all+"&roles="+encodeURIComponent(roles.join(","))+"&limit="+limit;
      setItems(await get<AnyRow[]>("/api/shortlist"+q));
    } catch { setItems([]); }
    finally { setBusy(false); }
  }
  useEffect(()=>{refresh();},[bat,bowl,all,roles.join(","),limit]);
  function toggle(role:string) { setRoles(old=>old.includes(role)?old.filter(x=>x!==role):[...old,role]); }
  return <><SectionTitle eyebrow="SQUAD BUILDING LAB" title="Build a squad with intent." detail="Tune role priorities and discover players using historical performance — without auction-price guesses."/>
    <div className="notice"><CircleHelp size={17}/> Statistical fit based on historical player impact. Not an official franchise requirement or future-performance prediction.</div>
    <div className="panel fit-controls">
      <div className="control-heading"><div><span className="eyebrow">SCOUTING BRIEF</span><h3>Set your squad priorities</h3></div><span className="result-count">{busy?"UPDATING…":items.length+" PLAYERS"}</span></div>
      <div className="priority-grid">
        {[["Batting priority",bat,setBat],["Bowling priority",bowl,setBowl],["All-rounder priority",all,setAll]].map(([label,value,setter]:any)=><label className="priority-control" key={label}><span>{label}</span><b>{Number(value).toFixed(2)}</b><input type="range" min="0" max="1" step="0.05" value={value} onChange={e=>setter(Number(e.target.value))}/></label>)}
      </div>
      <div className="filter-row"><div><span className="filter-label">PLAYER ROLES</span><div className="role-toggles">{["Batter","Bowler","All-rounder"].map(r=><button type="button" key={r} className={roles.includes(r)?"role-toggle selected":"role-toggle"} onClick={()=>toggle(r)}>{r}</button>)}</div></div><label className="min-impact">SHORTLIST SIZE <b>{limit}</b><input type="range" min="5" max="50" step="1" value={limit} onChange={e=>setLimit(Number(e.target.value))}/></label></div>
    </div>
    <div className="shortlist-grid">{items.map((p,i)=><article className="shortlist-card" key={p.player}><div className="shortlist-rank">RANK / {String(i+1).padStart(2,"0")} <span>{p.fit_category}</span></div><h3>{p.player}</h3><div className="fit-score"><strong>{num(p.franchise_fit_score*100,0)}</strong><span>FIT INDEX</span></div><div className="fit-meter"><i style={{width:(Math.min(100,p.franchise_fit_score*100))+"%"}}/></div><div className="fit-details"><span>Batting impact <b>{num(p.batting_impact)}</b></span><span>Bowling impact <b>{num(p.bowling_impact)}</b></span><span>Combined impact <b>{num(p.combined_impact)}</b></span></div></article>)}</div>
    {!busy&&!items.length&&<div className="empty-state">No players match these filters. Select at least one role.</div>}
  </>;
}


function WinProbability() {
  const [matches,setMatches]=useState<AnyRow[]>([]),[matchId,setMatchId]=useState(""),[data,setData]=useState<AnyRow|null>(null),[busy,setBusy]=useState(false),[message,setMessage]=useState("");
  useEffect(()=>{get<AnyRow[]>("/api/win-probability/matches").then(items=>{setMatches(items);if(items[0])setMatchId(String(items[0].match_id));}).catch(()=>setMessage("Could not load the historical match list."));},[]);
  useEffect(()=>{if(!matchId)return;setBusy(true);setMessage("");get<AnyRow>("/api/win-probability/"+encodeURIComponent(matchId)).then(setData).catch(()=>{setData(null);setMessage("This match has no complete two-innings delivery record available for replay.");}).finally(()=>setBusy(false));},[matchId]);
  return <><SectionTitle eyebrow="MODEL CENTRE" title="Every ball changes the story." detail="Replay historical chases using the saved Logistic Regression model and ball-by-ball delivery data."/>
    <div className="match-replay-toolbar"><label>SELECT HISTORICAL MATCH<select value={matchId} onChange={e=>setMatchId(e.target.value)}>{matches.map(m=><option value={m.match_id} key={m.match_id}>{m.label}</option>)}</select></label><span className="model-tag"><i/> LOGISTIC REGRESSION · HISTORICAL</span></div>
    {busy?<div className="loading">Calculating ball-by-ball probabilities…</div>:message?<div className="notice">{message}</div>:data&&<>
      <div className="metrics-grid three-metrics"><Metric label="Chasing team" value={data.chasing_team} note={"Target "+data.target+" runs"} icon={Shield}/><Metric label="Last valid model state" value={(Number(data.last_valid_wp)*100).toFixed(1)+"%"} note="Chasing team win probability" icon={Gauge}/><Metric label="Actual match winner" value={data.winner||"Unknown"} note="Recorded result, separate from model output" icon={Trophy}/></div>
      <div className="panel"><SectionTitle eyebrow="CHASE TIMELINE" title="Win probability by delivery" detail="Model probability for the chasing side at each valid ball state."/><div className="chart-wrap"><ResponsiveContainer width="100%" height={300}><AreaChart data={data.curve}><CartesianGrid stroke="#263244" vertical={false}/><XAxis dataKey="ball_num" stroke="#728096" tickLine={false} axisLine={false}/><YAxis domain={[0,1]} tickFormatter={(v)=>Math.round(v*100)+"%"} stroke="#728096" tickLine={false} axisLine={false}/><Tooltip formatter={(v:any)=>((Number(v)*100).toFixed(1)+"%")} labelFormatter={(v)=>"Ball "+v} contentStyle={{background:"#111b2a",border:"1px solid #2c394c",borderRadius:12}}/><Area type="monotone" dataKey="wp" stroke="#b7f36b" strokeWidth={2.5} fill="#b7f36b" fillOpacity={0.13}/></AreaChart></ResponsiveContainer></div><div className="match-context"><span>RUNS NEEDED <b>{data.curve[data.curve.length-1]?.runs_needed??"—"}</b></span><span>BALLS LEFT <b>{data.curve[data.curve.length-1]?.balls_left??"—"}</b></span><span>WICKETS LEFT <b>{data.curve[data.curve.length-1]?.wickets_left??"—"}</b></span></div></div>
      <div className="panel table-panel"><div className="table-heading">BALL-BY-BALL MODEL OUTPUT <span>{data.curve.length} STATES</span></div><div className="table-scroll"><table><thead><tr><th>BALL</th><th>BATTER TEAM</th><th>RUNS</th><th>NEEDED</th><th>BALLS LEFT</th><th>WICKETS LEFT</th><th>WIN PROBABILITY</th></tr></thead><tbody>{data.curve.filter((r:AnyRow,i:number)=>i%6===0||i===data.curve.length-1).map((r:AnyRow,i:number)=><tr key={i}><td>{r.ball_num}</td><td>{r.batting_team}</td><td>{r.runs_so_far}</td><td>{r.runs_needed}</td><td>{r.balls_left}</td><td>{r.wickets_left}</td><td>{(Number(r.wp)*100).toFixed(1)}%</td></tr>)}</tbody></table></div></div>
    </>}
  </>;
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

