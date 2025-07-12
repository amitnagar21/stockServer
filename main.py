from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from bs4 import BeautifulSoup
from urllib.parse import urlencode
import requests
import time

app = FastAPI()

# Allow all origins (or restrict to your frontend domain)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session setup
session = requests.Session()
home_url = "https://chartink.com/screener"
widget_url = "https://chartink.com/widget/process"

# Cache objects
cache = {
    "csrf_token": {"value": None, "timestamp": 0},
    "response": {"value": None, "timestamp": 0}
}

# Expiry settings
TOKEN_EXPIRY = 86400       # 24 hours
RESPONSE_EXPIRY = 300      # 5 minutes

# Function to get cached CSRF token or fetch a new one
def get_csrf_token():
    now = time.time()
    if cache["csrf_token"]["value"] and now - cache["csrf_token"]["timestamp"] < TOKEN_EXPIRY:
        return cache["csrf_token"]["value"]
    
    # Fetch new CSRF token
    resp = session.get(home_url)
    soup = BeautifulSoup(resp.text, "html.parser")
    token_tag = soup.find("meta", {"name": "csrf-token"})
    token = token_tag["content"] if token_tag else None

    # Cache token
    cache["csrf_token"]["value"] = token
    cache["csrf_token"]["timestamp"] = now
    return token

# Function to get Chartink data
def get_chartink_data():
    now = time.time()
    if cache["response"]["value"] and now - cache["response"]["timestamp"] < RESPONSE_EXPIRY:
        print(" Using cached Chartink response (valid within 5 min)")
        return cache["response"]["value"]
    
    # Fetch fresh response
    token = get_csrf_token()

    headers = {
        "X-CSRF-TOKEN": token,
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded",
        "Referer": "https://chartink.com/dashboard/347360"
    }

    payload = {
        "query": "select latest Close - 1 day ago Close / 1 day ago Close * 100 as '% Change', latest Close as 'Price', TTM PE as 'PE', latest Close - 4 weeks ago Close * 100 / 4 weeks ago Close as '4W Gain', latest Min( 20 , latest Low ) as '4W low', latest Max( 20 , latest Close ) as '4W high', Weekly Rsi( 14 ) as 'WRsi', latest Ema( latest High , 20 ) * 0.20 + latest Ema( latest High , 20 ) as 'Ai Prediction High ', latest Close * 0.07 - latest Close as 'Ai Prediction Low Level 1', latest Close * 0.1 - latest Close as 'Ai Prediction Low Level 2', Monthly Sma( ( Monthly Open - Monthly Low / Monthly Open * 100 ) , 12 ) * 0.01 * latest Close - latest Close as 'Ai Prediction Low Level 3' WHERE( {33489} ( latest max( 15 , latest rsi( 14 ) ) > 60 and latest min( 15 , latest rsi( 14 ) ) > 55 ) ) GROUP BY symbol ORDER BY 4 desc",
        "limit": 1000,
        "use_live": 1,
        "size": 1,
        "widget_id": 3651769
    }

    response = session.post(widget_url, data=payload, headers=headers)
    data = response.json()

    # Cache response
    cache["response"]["value"] = data
    cache["response"]["timestamp"] = now

    print(" Fetched fresh Chartink response")
    return data

# API endpoint
@app.get("/chartink")
def fetch_chartink():
    try:
        return get_chartink_data()
    except Exception as e:
        return {"error": str(e)}
