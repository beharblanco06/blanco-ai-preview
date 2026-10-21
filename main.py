import os, secrets, random, math
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
app = FastAPI(title="BLANCO SIM LAB", version="0.2.0")
class Request(BaseModel):
    sport: str
    home: str
    away: str
    home_mean: float = Field(gt=0, le=300)
    away_mean: float = Field(gt=0, le=300)
    home_sd: float = Field(gt=0, le=100)
    away_sd: float = Field(gt=0, le=100)
    correlation: float = Field(default=0, ge=-0.95, le=0.95)
    total_line: float | None = None
    home_spread: float | None = None
    simulations: int = Field(default=5000, ge=100, le=5000)
    seed: int = 42
@app.get("/")
def index():
    return {"name":"BLANCO SIM LAB","model":"input-driven Monte Carlo prototype","auto_data":False,"supported":["nba","nfl","nhl","mlb","soccer"],"docs":"/docs"}
@app.get("/health")
def health(): return {"status":"ok","max_simulations":5000,"auto_data":False}
@app.post("/simulate")
def simulate(req:Request, x_api_key: str|None=Header(default=None)):
    key = os.getenv("SIM_API_KEY")
    if not key: raise HTTPException(503,"SIM_API_KEY not configured")
    if not x_api_key or not secrets.compare_digest(x_api_key,key): raise HTTPException(401,"unauthorized")
    if req.sport.lower() not in {"nba","nfl","nhl","mlb","soccer"}: raise HTTPException(422,"unsupported sport")
    rng=random.Random(req.seed)
    homes=[]; aways=[]
    for _ in range(req.simulations):
        z1=rng.gauss(0,1); z2=rng.gauss(0,1)
        x=max(0,req.home_mean+req.home_sd*z1)
        y=max(0,req.away_mean+req.away_sd*(req.correlation*z1+math.sqrt(1-req.correlation**2)*z2))
        homes.append(int(round(x))); aways.append(int(round(y)))
    n=req.simulations
    wins=sum(h>a for h,a in zip(homes,aways))
    draws=sum(h==a for h,a in zip(homes,aways))
    totals=sorted(h+a for h,a in zip(homes,aways))
    def quantile(v,p): return v[int((len(v)-1)*p)]
    result={"sport":req.sport,"home":req.home,"away":req.away,"simulations":n,"model":"input-driven correlated-score Gaussian (NOT play-by-play)","source":"caller-provided means, volatility and correlation; NOT automatically sourced","home_win_probability":wins/n,"draw_probability":draws/n,"away_win_probability":(n-wins-draws)/n,"average_score":{"home":sum(homes)/n,"away":sum(aways)/n},"total_score_percentiles":{"p10":quantile(totals,.1),"p50":quantile(totals,.5),"p90":quantile(totals,.9)}}
    if req.total_line is not None:
        result["total_line"]=req.total_line
        result["under_probability"]=sum(t<req.total_line for t in totals)/n
        result["over_probability"]=sum(t>req.total_line for t in totals)/n
    if req.home_spread is not None:
        result["home_spread"]=req.home_spread
        result["home_cover_probability"]=sum(h+req.home_spread>a for h,a in zip(homes,aways))/n
    return result
