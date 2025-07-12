# main.py
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    return {"message": "Web service is live!"}

@app.get("/predict")
def predict():
    return {
        "price": 123.45,
        "confidence": 0.91,
        "status": "ok"
    }
