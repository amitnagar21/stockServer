from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from bs4 import BeautifulSoup
import requests
import time
import os

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session and URLs
session = requests.Session()
home_url = "https://chartink.com/screener"
widget_url = "https://chartink.com/widget/process"

# Cache for token and responses
cache = {
    "csrf_token": {"value": None, "timestamp": 0},
    "response_indexstat": {"value": None, "timestamp": 0},
    "response_allfno": {"value": None, "timestamp": 0},
    "response_consolidation15d": {"value": None, "timestamp": 0},
    "response_strong_mvmentum": {"value": None, "timestamp": 0},
    "response_strong_downtrend": {"value": None, "timestamp": 0}
}

# Expiry Settings
TOKEN_EXPIRY = 86400      # 24 hours
RESPONSE_EXPIRY = 300     # 5 minutes

# Get or refresh CSRF token
def get_csrf_token():
    now = time.time()
    if cache["csrf_token"]["value"] and now - cache["csrf_token"]["timestamp"] < TOKEN_EXPIRY:
        return cache["csrf_token"]["value"]

    resp = session.get(home_url)
    soup = BeautifulSoup(resp.text, "html.parser")
    token_tag = soup.find("meta", {"name": "csrf-token"})
    token = token_tag["content"] if token_tag else None

    cache["csrf_token"]["value"] = token
    cache["csrf_token"]["timestamp"] = now
    return token

# Fetch data from Chartink server
def fetch_server_data(query: str, cache_key: str, widget_id: int):
    now = time.time()
    if cache[cache_key]["value"] and now - cache[cache_key]["timestamp"] < RESPONSE_EXPIRY:
        print(f"Using cached response for {cache_key}")
        return cache[cache_key]["value"]

    token = get_csrf_token()
    headers = {
        "X-CSRF-TOKEN": token,
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded",
        "Referer": "https://chartink.com/dashboard/347360"
    }

    payload = {
        "query": query,
        "limit": 1000,
        "use_live": 1,
        "size": 1,
        "widget_id": widget_id
    }

    response = session.post(widget_url, data=payload, headers=headers)
    data = response.json()

    cache[cache_key]["value"] = data
    cache[cache_key]["timestamp"] = now
    print(f"Fetched fresh response for {cache_key}")
    return data

# ------------------ API ENDPOINTS ------------------

@app.get("/indexstat")
def get_indexstat():
    query = """
    SELECT   latestCLOSE                                                   as 'Ltp',
        latest "close - 1 candle ago close / 1 candle ago close * 100" AS '% chg',
        latestCLOSE - 2 weeks agoCLOSE * 100 / 2 weeks agoCLOSE     as '2W Gain',
        latestCLOSE - 3 weeks agoCLOSE * 100 / 3 weeks agoCLOSE     as '3W Gain',
        latestCLOSE - 4 weeks agoCLOSE * 100 / 4 weeks agoCLOSE     as '4W Gain',
        latestCLOSE - 1 month agoCLOSE * 100 / 1 month agoCLOSE     as 'This month',
        latestCLOSE - 10 weeks agoCLOSE * 100 / 10 weeks agoCLOSE   as '10W Gain',
        latestCLOSE - 3 months agoCLOSE * 100 / 3 months agoCLOSE   as '3M Gain',
        latestCLOSE - 6 months agoCLOSE * 100 / 6 months agoCLOSE   as '6M Gain',
        latestCLOSE - 1 quarter agoCLOSE * 100 / 1 quarter agoCLOSE as '1Q Gain',
        latestCLOSE - 3 quarter agoCLOSE * 100 / 3 quarter agoCLOSE as '3Q Gain',
        latestCLOSE - 1 year agoCLOSE * 100 / 1 year agoCLOSE       as '1Y Gain',
        latestCLOSE - 2 years agoCLOSE * 100 / 2 years agoCLOSE     as '2Y Gain',
        latestCLOSE - 5 years agoCLOSE * 100 / 5 years agoCLOSE     as '5Y Gain'
    WHERE    {45603} 1 = 1
    GROUP BY symbol
    ORDER BY 2 DESC
    """
    return fetch_server_data(query.strip(), "response_indexstat", 3656538)

@app.get("/all_fno_statistics")
def get_all_fno_statistics():
    query = """
    select latest "close - 1 candle ago close / 1 candle ago close * 100" as '% Change',
           latest Close as 'Price',
           Monthly "close - 1 candle ago close / 1 candle ago close * 100" as 'M %',
           Monthly Sma( Monthly "close - 1 candle ago close / 1 candle ago close * 100" * Monthly count( 1, 1 where monthly "close - 1 candle ago close / 1 candle ago close * 100" < 0 ) , 18 ) as 'Average Monthly fall by Close ',
           Monthly Sma( ( Monthly Open - Monthly Low / Monthly Open * 100 ) , 18 ) * -1 as 'Avg Max % Down',
           latest Close - 20 days ago Close * 100 / 20 days ago Close as '4W Gain',
           Monthly Sma( ( Monthly High - Monthly Open / Monthly Open * 100 ) , 18 ) as 'Avg Max % Up',
           Monthly Sma( Monthly "close - 1 candle ago close / 1 candle ago close * 100" * Monthly count( 1, 1 where monthly "close - 1 candle ago close / 1 candle ago close * 100" >= 0 ) , 18 ) as 'Average Monthly Gain by Close ',
           latest Close - 20 days ago Close * 100 / 20 days ago Close - Monthly Sma( ( Monthly High - Monthly Open / Monthly Open * 100 ) , 12 ) as '4W Gain Delta',
           Monthly Min( 18 , Monthly "close - 1 candle ago close / 1 candle ago close * 100" ) as '18M Max fall',
           Monthly Max( 18 , Monthly "close - 1 candle ago close / 1 candle ago close * 100" ) as '18M Max UP',
           latest Close - 10 days ago Close * 100 / 10 days ago Close as '2W Gain',
           latest Close - 15 days ago Close * 100 / 15 days ago Close as '3W Gain',
           latest Close - 30 days ago Close * 100 / 20 days ago Close as '6W Gain',
           latest Close - 40 days ago Close * 100 / 20 days ago Close as '8W Gain',
           Weekly Rsi( 14 ) as 'WRSI',
           Monthly Sma( ( Monthly Open - Monthly Low / Monthly Open * 100 ) , 12 ) * 0.01 * latest Close - latest Close as 'Ai Support'
    WHERE {33489} 1 = 1
    GROUP BY symbol
    ORDER BY 6 desc
    """
    return fetch_server_data(query.strip(), "response_allfno", 3654601)

@app.get("/consolidation15d")
def get_consolidation15d():
    query = """
    select Latest Close - 1 day ago Close / 1 day ago Close * 100 as '% Change',
           Latest Close as 'Price',
           Monthly Sma( ( Monthly High - Monthly Open / Monthly Open * 100 ) , 12 ) * 0.01 * Weekly Max( 5 , Weekly High ) + Weekly Max( 5 , Weekly High ) as 'Sell Range 2',
           Latest Rsi( 14 ) as 'Rsi',
           Weekly Rsi( 14 ) as 'WRsi',
           Latest Sma( Latest Rsi( 14 ) , 14 ) - Latest Rsi( 14 ) as 'Avg RSI Delta',
           Latest Rsi( 14 ) - Latest Sma( Latest Rsi( 14 ) , 14 ) as 'Delta',
           Weekly Min( 5 , Weekly Low ) as '5W low',
           Weekly Max( 5 , Weekly High ) as '5W High',
           Latest Close - 1 month ago Close * 100 / 1 month ago Close as 'This month',
           Latest Close - 2 weeks ago Close * 100 / 2 weeks ago Close as '2W Gain',
           Latest Close - 3 weeks ago Close * 100 / 3 weeks ago Close as '3W Gain',
           Latest Close - 4 weeks ago Close * 100 / 4 weeks ago Close as '4W Gain'
    WHERE( {33489} ( latest max( 10 , latest rsi( 14 ) ) < 60 and latest min( 10 , latest rsi( 14 ) ) > 40 ) )
    GROUP BY symbol
    ORDER BY 1 desc
    """
    return fetch_server_data(query.strip(), "response_consolidation15d", 3656567)

@app.get("/strong_mvmentum")
def get_strong_mvmentum():
    query = """
    select Market Cap as 'MCap',
           latest Close - 1 day ago Close / 1 day ago Close * 100 as '% Change',
           latest Close as 'Price',
           Weekly Max( 52 , Weekly High ) as '52 high',
           Yearly PE Ratio as 'PE',
           latest Close - 10 days ago Close * 100 / 10 days ago Close as '2W Gain'
    WHERE( {cash} (
        latest rsi( 14 ) > 60 and
        1 day ago rsi( 14 ) > 60 and
        2 days ago rsi( 14 ) > 60 and
        3 days ago rsi( 14 ) > 60 and
        4 days ago rsi( 14 ) > 60 and
        latest close = latest max( 20 , latest close ) * 1 and
        market cap > 5000
    ) )
    GROUP BY symbol
    ORDER BY 2 desc
    """
    return fetch_server_data(query.strip(), "response_strong_mvmentum", 3654496)

@app.get("/strong_downtrend")
def get_strong_downtrend():
    query = """
    select Market Cap as 'MCap',
           latest Close - 1 day ago Close / 1 day ago Close * 100 as '% Change',
           latest Close as 'Price',
           Weekly Max( 52 , Weekly High ) as '52 high',
           Yearly PE Ratio as 'PE',
           latest Close - 10 days ago Close * 100 / 10 days ago Close as '2W Gain'
    WHERE( {cash} (
        latest rsi( 14 ) < 40 and
        1 day ago rsi( 14 ) < 40 and
        2 days ago rsi( 14 ) < 40 and
        3 days ago rsi( 14 ) < 40 and
        4 days ago rsi( 14 ) < 40 and
        market cap > 5000
    ) )
    GROUP BY symbol
    ORDER BY 2 desc
    """
    return fetch_server_data(query.strip(), "response_strong_downtrend", 3657355)



