import json
import time
from collections import deque
from contextlib import asynccontextmanager
from mcp.server.fastmcp import FastMCP
from main import app
from auto_sim import run, DataError

mcp = FastMCP("BLANCO SIM LAB", stateless_http=True, json_response=True)
recent = deque()

@mcp.tool()
def simulate_game(matchup: str, sport: str = "", league: str = "", date: str = "") -> str:
    """Given JUST a matchup like 'Bucks vs Wizards' or 'Arsenal vs Chelsea', automatically retrieve past ESPN team results and execute exactly 5,000 score Monte Carlo draws. NBA, NFL, NHL, MLB, soccer supported. Optional league: epl, la liga, bundesliga, serie a, ucl, mls. Response distinguishes actual data from heuristic modeling. NEVER call these possession-by-possession simulations. Player stats and odds are NOT simulated."""
    now=time.monotonic()
    while recent and now-recent[0]>60:recent.popleft()
    if len(recent)>=15:return json.dumps({"error":"Rate limit reached; retry shortly","trials":0})
    recent.append(now)
    try:return json.dumps(run(matchup,sport,league,date))
    except DataError as exc:return json.dumps({"error":str(exc),"trials":0})

@asynccontextmanager
async def lifespan(application):
    async with mcp.session_manager.run():
        yield

app.router.lifespan_context=lifespan
app.mount("/", mcp.streamable_http_app())
