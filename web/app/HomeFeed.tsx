"use client";

import { useEffect, useState } from "react";
import { Activity, ArrowRight, CalendarDays, ChevronRight, Clock3, Shield, Trophy, Users } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
type Match = { match_id:number|string; season:number|string; date:string; team1:string; team2:string; winner?:string|null; result?:string; player_of_match?:string|null; venue?:string };
type Summary = { matches:number; seasons:number; firstSeason:string; lastSeason:string; players:number; teams:number };
type Team = { team:string; played:number; wins:number; winRate:number };

function dateLabel(value:string) {
  const d=new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleDateString("en-IN",{day:"2-digit",month:"short",year:"numeric"});
}

export default function HomeFeed({ onNavigate }: { onNavigate:(page:any)=>void }) {
  const [matches,setMatches]=useState<Match[]>([]);
  const [summary,setSummary]=useState<Summary|null>(null);
  const [teams,setTeams]=useState<Team[]>([]);
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState("");

  useEffect(()=>{
    Promise.all([
      fetch(API+"/api/results?limit=10",{cache:"no-store"}).then(r=>{if(!r.ok)throw new Error("Could not load IPL results");return r.json();}),
      fetch(API+"/api/overview",{cache:"no-store"}).then(r=>{if(!r.ok)throw new Error("Could not load IPL overview");return r.json();}),
      fetch(API+"/api/teams",{cache:"no-store"}).then(r=>{if(!r.ok)throw new Error("Could not load teams");return r.json();})
    ]).then(([m,o,t])=>{
      setMatches(m);
      setSummary(o.summary);
      setTeams(t.sort((a:Team,b:Team)=>b.wins-a.wins).slice(0,6));
    }).catch(e=>setError(e.message||"Unable to connect to the IPL data service."))
      .finally(()=>setLoading(false));
  },[]);

  return <div className="home-feed">
    <div className="crex-home-head">
      <div><span className="home-kicker">INDIAN PREMIER LEAGUE</span><h1>Cricket home</h1><p>Scores, results and IPL records — all in one place.</p></div>
      <button className="crex-all-matches" onClick={()=>onNavigate("Live Centre")}>All matches <ArrowRight size={14}/></button>
    </div>

    <div className="crex-home-tabs" aria-label="Cricket sections">
      <button className="selected" onClick={()=>onNavigate("Home")}>Home</button>
      <button onClick={()=>onNavigate("Live Centre")}>Matches</button>
      <button onClick={()=>onNavigate("Teams")}>Teams</button>
      <button onClick={()=>onNavigate("Players")}>Players</button>
      <button onClick={()=>onNavigate("Venues")}>Venues</button>
    </div>

    <div className="crex-data-strip">
      <div><span className="crex-data-dot"/> <b>IPL ARCHIVE</b><small>Historical data</small></div>
      <div><strong>{summary?.lastSeason || "—"}</strong><small>Latest season</small></div>
      <div><strong>{summary?.matches.toLocaleString("en-IN") || "—"}</strong><small>Matches</small></div>
      <div><strong>{summary?.teams ?? "—"}</strong><small>Teams</small></div>
      <div><strong>{summary?.players.toLocaleString("en-IN") || "—"}</strong><small>Players</small></div>
    </div>

    {error&&<div className="home-error">{error}</div>}
    <div className="crex-home-layout">
      <section className="crex-main-column">
        <div className="crex-section-bar"><div><span className="home-kicker">MATCH CENTRE</span><h2>Latest IPL results</h2></div><button onClick={()=>onNavigate("Live Centre")}>View all <ChevronRight size={14}/></button></div>
        <div className="crex-match-list">
          {loading?<div className="home-loading">Loading match records…</div>:matches.map(m=><article className="crex-match-row" key={m.match_id}>
            <div className="crex-match-topline"><span>IPL {m.season} <i>•</i> {dateLabel(m.date)}</span><b className="crex-result-tag">RESULT</b></div>
            <div className="crex-match-teams">
              <div><span className="crex-team-badge">{m.team1.split(" ").map(x=>x[0]).join("").slice(0,3)}</span><b>{m.team1}</b>{m.winner===m.team1&&<Trophy size={13}/>}</div>
              <div><span className="crex-team-badge">{m.team2.split(" ").map(x=>x[0]).join("").slice(0,3)}</span><b>{m.team2}</b>{m.winner===m.team2&&<Trophy size={13}/>}</div>
            </div>
            <div className="crex-match-bottom"><strong>{m.winner ? m.winner+" won" : "Match tied / no result"}{m.result&&m.result!=="No result"?" · "+m.result:""}</strong><span>{m.venue||"Venue unavailable"}</span></div>
            {m.player_of_match&&<div className="crex-potm">PLAYER OF THE MATCH <b>{m.player_of_match}</b></div>}
          </article>)}
          {!loading&&!matches.length&&!error&&<div className="home-loading">No historical match records are available.</div>}
        </div>
        <p className="home-data-note">These are completed historical matches from the processed IPL archive. They are not live fixtures or live scores.</p>
      </section>

      <aside className="crex-side-column">
        <section className="crex-side-panel">
          <div className="crex-section-bar"><div><span className="home-kicker">QUICK ACCESS</span><h2>Explore IPL</h2></div></div>
          <button className="crex-shortcut" onClick={()=>onNavigate("Live Centre")}><Activity/><span><b>Live match centre</b><small>Provider-connected coverage</small></span><ChevronRight/></button>
          <button className="crex-shortcut" onClick={()=>onNavigate("Teams")}><Shield/><span><b>Team records</b><small>Franchise performance</small></span><ChevronRight/></button>
          <button className="crex-shortcut" onClick={()=>onNavigate("Players")}><Users/><span><b>Player statistics</b><small>Career and season numbers</small></span><ChevronRight/></button>
          <button className="crex-shortcut" onClick={()=>onNavigate("Venues")}><CalendarDays/><span><b>Venue records</b><small>Ground-wise IPL history</small></span><ChevronRight/></button>
        </section>

        <section className="crex-side-panel crex-rank-panel">
          <div className="crex-section-bar"><div><span className="home-kicker">FRANCHISE RECORDS</span><h2>Most IPL wins</h2></div><button onClick={()=>onNavigate("Teams")}>All <ChevronRight size={13}/></button></div>
          {teams.map((t,i)=><div className="crex-rank-row" key={t.team}><span>{i+1}</span><b>{t.team}</b><strong>{t.wins}</strong></div>)}
        </section>

        <section className="crex-live-note"><span className="crex-data-dot"/> <b>Live coverage status</b><p>Live scores and upcoming fixtures appear here only when the connected data provider includes those endpoints in its plan.</p><small><Clock3 size={12}/> No generated or simulated scores</small></section>
      </aside>
    </div>
  </div>;
}
