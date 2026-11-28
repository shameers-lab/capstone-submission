import logging
from datetime import datetime
from pathlib import Path

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from ..feature_utils import MODEL_FEATURES, add_model_features

logger = logging.getLogger(__name__)
PART3_DIR = Path(__file__).resolve().parents[1]
MODEL_PATH = PART3_DIR / "models" / "proxy_risk_classifier.joblib"
if not MODEL_PATH.is_file():
    raise FileNotFoundError(
        f"Trained model is unavailable at {MODEL_PATH}; run the Part 3 training command first."
    )
MODEL = joblib.load(MODEL_PATH)
app = FastAPI(
    title="Metro Traffic Proxy Classification Demo",
    version="1.0.0",
    description=(
        "Educational mock deployment. The model predicts a congestion/weather proxy label, "
        "not real accident likelihood or safety."
    ),
)


class PredictionRequest(BaseModel):
    date_time: datetime
    holiday: str = "Unknown"
    temp: float = Field(ge=150, le=400, description="Temperature in Kelvin")
    rain_1h: float = Field(ge=0, description="Rainfall in millimetres during the previous hour")
    snow_1h: float = Field(ge=0, description="Snowfall in millimetres during the previous hour")
    clouds_all: float = Field(ge=0, le=100, description="Cloud cover on source scale, 0 to 100")
    weather_main: str


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "model": MODEL_PATH.name}


@app.post("/predict")
def predict(request: PredictionRequest) -> dict[str, object]:
    row = pd.DataFrame(
        [
            {
                "date_time": request.date_time,
                "holiday": request.holiday.strip() or "Unknown",
                "temp": request.temp,
                "rain_1h": request.rain_1h,
                "snow_1h": request.snow_1h,
                "clouds_all": request.clouds_all,
                "weather_main": request.weather_main.strip() or "Unknown",
            }
        ]
    )
    features = add_model_features(row)
    try:
        probability = float(MODEL.predict_proba(features[MODEL_FEATURES])[0, 1])
    except (ValueError, KeyError) as exc:
        logger.exception("Prediction failed for validly parsed request.")
        raise HTTPException(status_code=422, detail="Input could not be processed by the model.") from exc
    logger.info("Generated proxy prediction for %s.", request.date_time.isoformat())
    return {
        "proxy_positive": probability >= 0.5,
        "proxy_probability": probability,
        "threshold": 0.5,
        "model_version": "1.0",
        "warning": (
            "This output is not an accident prediction, does not estimate actual accident likelihood, "
            "and must not be used for real-world safety decisions."
        ),
    }
