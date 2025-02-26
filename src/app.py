from fastapi import FastAPI
import mlflow.pyfunc
import os

app = FastAPI()

# Charger le modèle depuis MLflow Model Registry
model_name = os.getenv("MODEL_NAME", "gradient_boosting")
model = mlflow.pyfunc.load_model(f"/mlruns/models/{model_name}")


@app.get("/")
def home():
    return {"message": "API de scoring du modèle MLflow"}

@app.post("/predict")
def predict(data: dict):
    import pandas as pd
    df = pd.DataFrame([data])
    prediction = model.predict(df)
    return {"prediction": prediction.tolist()}
