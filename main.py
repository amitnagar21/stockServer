from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from bs4 import BeautifulSoup
import requests
import time
import openai
import os

app = FastAPI()

# Set your OpenAI API key
openai.api_key = "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"  # <-- Replace with your API key

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

@app.post("/ask")
async def ask_gpt(request: Request):
    body = await request.json()
    prompt = body.get("prompt")

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",  # or "gpt-3.5-turbo"
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return {
            "response": response['choices'][0]['message']['content']
        }
    except Exception as e:
        return {"error": str(e)}
