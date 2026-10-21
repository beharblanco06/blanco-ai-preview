import datetime as dt
import difflib
import json
import math
import random
import re
import statistics
import urllib.request
from functools import lru_cache

BASE = "https://site.api.espn.com/apis/site/v2/sports/"
LEAGUES = {"nba":"basketball/nba","nfl":"football/nfl","nhl":"hockey/nhl","mlb":"baseball/mlb",
           "epl":"soccer/eng.1","la liga":"soccer/esp.1","bundesliga":"soccer/ger.1",
           "serie a":"soccer/ita.1","ucl":"soccer/uefa.champions","mls":"soccer/usa.1"}
SPORTS = {"nba":["nba"],"nfl":["nfl"],"nhl":["nhl"],"mlb":["mlb"],
          "soccer":["epl","la liga","bundesliga","serie a","ucl","mls"]}
PRIOR = {"nba":(113,13),"nfl":(23,12),"nhl":(3,1.8),"mlb":(4.5,3.1),"soccer":(1.4,1.35)}
class DataError(Exception): pass

@lru_cache(maxsize=160)
def get(url):
    req=urllib.request.Request(url,headers={"Accept":"application/json","User-Agent":"BLANCO-SIM-LAB/0.2"})
    try:
        with urllib.request.urlopen(req,timeout=12) as result:return json.load(result)
    except Exception as exc:raise DataError("Sports data API unavailable: "+type(exc).__name__)

def normalize(s):return re.sub(r"[^a-z0-9 ]","",str(s).lower()).strip()
def find_teams(payload):
    matches={}
    def recurse(v):
        if isinstance(v,dict):
            t=v.get("team")
            if isinstance(t,dict) and t.get("id") and t.get("displayName"):matches[str(t["id"])]=t
            for item in v.values():recurse(item)
        elif isinstance(v,list):
            for item in v:recurse(item)
    recurse(payload)
    return list(matches.values())

def team_lookup(name,teams):
    query=normalize(name)
    choices=[]
    for t in teams:
        vals=[normalize(t.get(k,"")) for k in ("displayName","name","shortDisplayName","abbreviation","nickname")]
        vals.append(normalize(t["displayName"]).split(" ")[-1])
        if query in vals:score=1
        elif any(v.endswith(" "+query) for v in vals):score=.92
        else:score=max(difflib.SequenceMatcher(None,query,v).ratio() for v in vals)
        choices.append((score,t))
    choices.sort(key=lambda x:x[0],reverse=True)
    if not choices or choices[0][0]<.68:raise DataError("Team not recognized: "+name)
    return choices[0][1]

def numeric(score):
    if isinstance(score,dict):score=score.get("value",score.get("displayValue"))
    try:return float(score)
    except (ValueError,TypeError):return None

def history(league,team_id,cutoff):
    sport=league if league in ("nba","nfl","nhl","mlb") else "soccer"
    season=cutoff.year+(1 if sport in ("nba","nhl") else 0)
    results=[];all_events=[]
    for yr in (season,season-1,season-2):
        try:payload=get(BASE+LEAGUES[league]+f"/teams/{team_id}/schedule?season={yr}&limit=200")
        except DataError:continue
        events=payload.get("events",[])
        all_events.extend(events)
        for e in events:
            try:
                stamp=dt.datetime.fromisoformat(e["date"].replace("Z","+00:00"))
                if stamp>=cutoff:continue
                c=e["competitions"][0]["competitors"]
                state=e.get("status",{}).get("type",{})
                if state.get("state")!="post" and not state.get("completed"):continue
                us=next(x for x in c if str(x["team"]["id"])==str(team_id))
                other=next(x for x in c if str(x["team"]["id"])!=str(team_id))
                scored=numeric(us.get("score"));allowed=numeric(other.get("score"))
                if scored is not None and allowed is not None:results.append((stamp,scored,allowed))
            except (KeyError,IndexError,StopIteration,TypeError,ValueError):pass
        if len(results)>=18:break
    unique={row[0].isoformat():row for row in results}
    return sorted(unique.values(),reverse=True)[:18],all_events

def poisson(rng,lam):
    x=1.;n=0;threshold=math.exp(-max(lam,0))
    while x>threshold:n+=1;x*=rng.random()
    return n-1

def run(matchup:str,sport:str="",league:str="",date:str=""):
    pieces=re.split(r"\s+(?:vs\.?|versus|at|@)\s+",matchup.strip(),maxsplit=1,flags=re.I)
    if len(pieces)!=2:raise DataError("Use 'Bucks vs Wizards' or 'Arsenal vs Chelsea'")
    sport=sport.lower().strip();league=league.lower().strip()
    if sport and sport not in SPORTS:raise DataError("Supported sports: nba, nfl, nhl, mlb, soccer")
    if league and league not in LEAGUES:raise DataError("Unknown league")
    if sport and league and league not in SPORTS[sport]:raise DataError("League conflicts with sport")
    try:
        cutoff=dt.datetime.strptime(date,"%Y-%m-%d").replace(tzinfo=dt.timezone.utc) if date else dt.datetime.now(dt.timezone.utc)
    except ValueError:raise DataError("Date must be YYYY-MM-DD")
    candidates=[league] if league else SPORTS[sport] if sport else list(LEAGUES)
    failures=[]
    for key in candidates:
        try:
            teams=find_teams(get(BASE+LEAGUES[key]+"/teams?limit=300"))
            if not teams:raise DataError("No ESPN team listing")
            a=team_lookup(pieces[0],teams);b=team_lookup(pieces[1],teams)
            if a["id"]==b["id"]:raise DataError("Same team on both sides")
            aa,events=history(key,a["id"],cutoff);bb,_=history(key,b["id"],cutoff)
            if min(len(aa),len(bb))<3:raise DataError("Insufficient completed-game sample")
            s=key if key in PRIOR else "soccer"
            prior,sd=PRIOR[s]
            def avg(values):return (len(values)*statistics.mean(values)+10*prior)/(len(values)+10)
            mu_a=(avg([r[1] for r in aa])+avg([r[2] for r in bb]))/2
            mu_b=(avg([r[1] for r in bb])+avg([r[2] for r in aa]))/2
            fixture=None
            for e in events:
                try:
                    c=e["competitions"][0]["competitors"]
                    if {str(x["team"]["id"]) for x in c}!={str(a["id"]),str(b["id"])}:continue
                    stamp=dt.datetime.fromisoformat(e["date"].replace("Z","+00:00"))
                    if fixture is None or abs((stamp-cutoff).total_seconds())<abs((fixture[0]-cutoff).total_seconds()):fixture=(stamp,c)
                except (KeyError,IndexError,TypeError,ValueError):pass
            if fixture:
                home=next((str(x["team"]["id"]) for x in fixture[1] if x.get("homeAway")=="home"),"")
                if home==str(a["id"]):mu_a*=1.025;mu_b*=.975
                elif home==str(b["id"]):mu_b*=1.025;mu_a*=.975
            rng=random.Random(42);scores=[]
            for _ in range(5000):
                if s in ("soccer","nhl","mlb"):x,y=poisson(rng,mu_a),poisson(rng,mu_b)
                else:x,y=max(0,round(rng.gauss(mu_a,sd))),max(0,round(rng.gauss(mu_b,sd)))
                scores.append((x,y))
            a_win=sum(x>y for x,y in scores);b_win=sum(x<y for x,y in scores)
            totals=sorted(x+y for x,y in scores)
            return {"mode":"AUTO_FORM_SCORE_SIM","model":"5,000 draws from recent team scores and allowed scores with league priors; NOT event/play-by-play",
                "sport":s,"league":key,"team_a":a["displayName"],"team_b":b["displayName"],"trials":5000,"seed":42,
                "game_date":fixture[0].isoformat() if fixture else None,"scheduled_fixture_verified":bool(fixture),
                "model_score":{"team_a":round(mu_a,2),"team_b":round(mu_b,2)},
                "team_a_win_probability":round(a_win/5000,4),"team_b_win_probability":round(b_win/5000,4),
                "draw_or_regulation_tie_probability":round((5000-a_win-b_win)/5000,4),
                "total_median":totals[2500],"total_p10":totals[500],"total_p90":totals[4500],
                "history_sample":{"team_a":len(aa),"team_b":len(bb)},
                "source":"ESPN unofficial team schedule final scores",
                "limitations":["No historical play-by-play or defensive matchups","No player props or injuries","No current sportsbook lines","Uncalibrated heuristic predictions; not betting-quality"],
                "confidence":"ILLUSTRATIVE ONLY"}
        except DataError as exc:failures.append(f"{key}: {exc}")
    raise DataError("Could not reliably simulate this matchup: "+"; ".join(failures[:3]))
