from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from bs4 import BeautifulSoup
import requests
import time

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
    "response_consolidation15d": {"value": None, "timestamp": 0}
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

# 1. /indexstat → Widget ID: 3656538
@app.get("/indexstat")
def get_indexstat():
    query = """
    select latest Close as 'Ltp',
           latest Close - latest Ema( latest Close , 200 ) as '200 EMA',
           latest "close - 1 candle ago close / 1 candle ago close * 100" as '% chg',
           1 month ago Close as 'MCose',
           latest Close - 1 month ago Close * 100 / 1 month ago Close as 'This month',
           latest Close - 2 weeks ago Close * 100 / 2 weeks ago Close as '2W Gain',
           latest Close - 3 weeks ago Close * 100 / 3 weeks ago Close as '3W Gain',
           latest Close - 4 weeks ago Close * 100 / 4 weeks ago Close as '4W Gain',
           latest Rsi( 14 ) as 'RSI',
           latest Sma( ( latest High - latest Low ) / latest Close * 100 , 15 ) * latest Close * 0.01 as 'Iv15P',
           Monthly Sma( Monthly "close - 1 candle ago close / 1 candle ago close * 100" * Monthly count( 1, 1 where monthly "close - 1 candle ago close / 1 candle ago close * 100" < 0 ) , 18 ) as 'Average M fall',
           2 weeks ago Sma( 2 weeks ago "close - 1 candle ago close / 1 candle ago close * 100" * 2 weeks ago count( 1, 1 where 2 weeks ago "close - 1 candle ago close / 1 candle ago close * 100" < 0 ) , 50 ) as 'Average fall',
           2 weeks ago Sma( 2 weeks ago "close - 1 candle ago close / 1 candle ago close * 100" * 2 weeks ago count( 1, 1 where 2 weeks ago "close - 1 candle ago close / 1 candle ago close * 100" >= 0 ) , 50 ) as 'Average gain',
           Monthly Sma( Monthly "close - 1 candle ago close / 1 candle ago close * 100" * Monthly count( 1, 1 where monthly "close - 1 candle ago close / 1 candle ago close * 100" >= 0 ) , 18 ) as 'Average M gain',
           Weekly Sma( Weekly "close - 1 candle ago close / 1 candle ago close * 100" * Weekly count( 1, 1 where weekly "close - 1 candle ago close / 1 candle ago close * 100" >= 0 ) , 50 ) as 'Average W gain'
    WHERE {45603} 1 = 1
    GROUP BY symbol
    ORDER BY 3 desc
    """
    return fetch_server_data(query.strip(), "response_indexstat", 3656538)

# 2. /all_fno_statistics → Widget ID: 3651769
@app.get("/all_fno_statistics")
def get_all_fno_statistics():
    query = """
    select latest Close - 1 day ago Close / 1 day ago Close * 100 as '% Change',
           latest Close as 'Price',
           TTM PE as 'PE',
           latest Close - 4 weeks ago Close * 100 / 4 weeks ago Close as '4W Gain',
           latest Min( 20 , latest Low ) as '4W low',
           latest Max( 20 , latest Close ) as '4W high',
           Weekly Rsi( 14 ) as 'WRsi',
           latest Ema( latest High , 20 ) * 0.20 + latest Ema( latest High , 20 ) as 'Ai Prediction High ',
           latest Close * 0.07 - latest Close as 'Ai Prediction Low Level 1',
           latest Close * 0.1 - latest Close as 'Ai Prediction Low Level 2',
           Monthly Sma( ( Monthly Open - Monthly Low / Monthly Open * 100 ) , 12 ) * 0.01 * latest Close - latest Close as 'Ai Prediction Low Level 3'
    WHERE( {33489} ( latest max( 15 , latest rsi( 14 ) ) > 60 and latest min( 15 , latest rsi( 14 ) ) > 55 ) )
    GROUP BY symbol
    ORDER BY 4 desc
    """
    return fetch_server_data(query.strip(), "response_allfno", 3651769)

# 3. /consolidation15d → Widget ID: 3656567
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
