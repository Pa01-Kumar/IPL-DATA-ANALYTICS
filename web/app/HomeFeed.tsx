"use client";

import { useEffect, useState } from "react";
import { Activity, ArrowRight, CalendarDays, ChevronRight, Clock3, Shield, Trophy, Users } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
type Match = { match_id: number|string; season: number|string; date: string; team1: string; team2: string; winner?: string|null; result?: string; player_of_match?: string|null; venue?: string };
type Summary = { matches:number; seasons:number; firstSeason:string; lastSeason:string; players:number; teams:number };
type Team = { team:string; played:number; wins:number; winRate:number };

function dateLabel(value:string) {
  const d=new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleDateString("en-IN",{day:"numeric",month:"short",year:"numeric"});
}

export default function HomeFeed({ onNavigate }: { onNavigate:(page:any)=>void }) {
  const [matches,setMatches]=useState<Match[]>([]);
  const [summary,setSummary]=useState<Summary|null>(null);
  const [teams,setTeams]=useState<Team[]>([]);
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState("");

  useEffect(()=>{
    Promise.all([
      fetch(API+"/api/results?limit=8",{cache:"no-store"}).then(r=>{if(!r.ok)throw new Error("Could not load IPL results");return r.json();}),
      fetch(API+"/api/overview",{cache:"no-store"}).then(r=>{if(!r.ok)throw new Error("Could not load IPL overview");return r.json();}),
      fetch(API+"/api/teams",{cache:"no-store"}).then(r=>{if(!r.ok)throw new Error("Could not load teams");return r.json();})
    ]).then(([m,o,t])=>{setMatches(m);setSummary(o.summary);setTeams(t.sort((a:Team,b:Team)=>b.wins-a.wins).slice(0,5));})
      .catch(e=>setError(e.message||"Unable to connect to the IPL data service."))
      .finally(()=>setLoading(false));
  },[]);

  return <div className="home-feed">
    <div className="home-welcome">
      <div><span className="home-kicker">WELCOME TO IPL INTELLIGENCE</span><h1>Every match.<br/><em>Every number.</em></h1>
      <p>Follow the IPL archive, explore team records and discover the numbers behind the game.</p>
      <button className="home-primary" onClick={()=>onNavigate("Live Centre")}>Open Match Centre <ArrowRight size={16}/></button></div>
      <div className="home-season-mark"><Trophy size={28}/><span>IPL ARCHIVE</span><b>{summary?.lastSeason || "—"}</b><small>SEASON DATA</small></div>
    </div>

    <div className="home-quick-links">
      <button onClick={()=>onNavigate("Live Centre")}><Activity/><span><b>Matches</b><small>Live & results</small></span><ChevronRight/></button>
      <button onClick={()=>onNavigate("Teams")}><Shield/><span><b>Teams</b><small>Franchise records</small></span><ChevronRight/></button>
      <button onClick={()=>onNavigate("Players")}><Users/><span><b>Players</b><small>Career statistics</small></span><ChevronRight/></button>
      <button onClick={()=>onNavigate("Venues")}><CalendarDays/><span><b>Venues</b><small>Ground records</small></span><ChevronRight/></button>
    </div>

    {summary&&<div className="home-stat-strip">
      <div><b>{summary.matches.toLocaleString("en-IN")}</b><span>MATCHES</span></div>
      <div><b>{summary.seasons}</b><span>SEASONS</span></div>
      <div><b>{summary.teams}</b><span>TEAMS</span></div>
      <div><b>{summary.players.toLocaleString("en-IN")}</b><span>PLAYERS</span></div>
    </div>}

    <div className="home-section-head"><div><span className="home-kicker">FROM THE IPL ARCHIVE</span><h2>Recent match results</h2><p>Completed matches from the latest available historical records.</p></div><button onClick={()=>onNavigate("Live Centre")}>All results <ArrowRight size={15}/></button></div>
    {error&&<div className="home-error">{error}</div>}
    {loading?<div className="home-loading">Loading match records…</div>:<div className="home-match-grid">
      {matches.map(m=><article className="home-match-card" key={m.match_id}>
        <div className="home-match-meta"><span>IPL {m.season}</span><span>{dateLabel(m.date)}</span></div>
        <div className="home-team-line"><b>{m.team1}</b>{m.winner===m.team1&&<Trophy size={14}/>}</div>
        <div className="home-team-line"><b>{m.team2}</b>{m.winner===m.team2&&<Trophy size={14}/>}</div>
        <div className="home-match-result">{m.winner ? m.winner+" won" : "No result"}{m.result&&m.result!=="No result"?" · "+m.result:""}</div>
        <div className="home-match-foot">{m.venue||"Venue unavailable"}{m.player_of_match&&<span> • POTM: {m.player_of_match}</span>}</div>
      </article>)}
      {!matches.length&&!error&&<div className="home-loading">No historical match records are available.</div>}
    </div>}

    <div className="home-lower-grid">
      <section className="home-panel"><div className="home-section-head compact"><div><span className="home-kicker">FRANCHISE RECORDS</span><h2>Most IPL wins</h2></div><button onClick={()=>onNavigate("Teams")}>View teams <ArrowRight size={14}/></button></div>
        {teams.map((t,i)=><div className="home-team-rank" key={t.team}><span>{String(i+1).padStart(2,"0")}</span><b>{t.team}</b><strong>{t.wins} wins</strong></div>)}
      </section>
      <section className="home-panel home-live-panel"><span className="home-kicker">MATCH CENTRE</span><Activity size={24}/><h2>Follow the game</h2><p>Open the Match Centre for provider-connected live coverage and the historical results archive. Live access depends on your cricket data plan.</p><button onClick={()=>onNavigate("Live Centre")}>Go to Match Centre <ArrowRight size={15}/></button><small><Clock3 size={12}/> No simulated live scores</small></section>
    </div>
    <p className="home-data-note">Historical statistics are calculated from the project's processed IPL dataset. Live scores and upcoming fixtures are shown only when an authorised provider feed is available.</p>
  </div>;
}
