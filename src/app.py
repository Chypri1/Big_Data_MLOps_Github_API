import json
from fastapi import FastAPI
import mlflow.pyfunc
from mlflow.tracking import MlflowClient
import pandas as pd
from pydantic import BaseModel
from threading import Lock
mlflow.set_tracking_uri("http://mlflow:8083")
# Charger le modèle depuis MLflow Registry
MODEL_NAME = "random_forest"  # Mets ton modèle ici
STAGE = "Production"

client = MlflowClient()
latest_model = client.get_latest_versions(MODEL_NAME, stages=[STAGE])[0]
model = mlflow.pyfunc.load_model(latest_model.source)
print(f"✅ Modèle chargé depuis {latest_model.source}")

labels_path = f"./{MODEL_NAME}_labels.json"
with open(labels_path, "r") as f:
    labels = json.load(f)
# Initialiser FastAPI
app = FastAPI(title="ML Model API", description="API pour faire des prédictions avec MLflow", version="1.0")

# Définir un schéma pour les données entrantes
class InputData(BaseModel):
    data: list  # Liste d'observations sous forme de listes

# Endpoint pour faire des prédictions
@app.post("/predict")
async def predict(input_data: InputData):
    df = pd.DataFrame(input_data.data)  # Convertir en DataFrame
    predictions = model.predict(df)  # Faire une prédiction
    language_predictions = [labels[p] for p in predictions]
    return {"predictions": language_predictions}  # Retourner en JSON

# 🔒 Verrou pour éviter plusieurs chargements simultanés
model_lock = Lock()

@app.post("/reload")
async def reload_model():
    global model
    with model_lock:
        latest_model = client.get_latest_versions(MODEL_NAME, stages=[STAGE])[0]
        model = mlflow.pyfunc.load_model(latest_model.source)
    return {"message": f"✅ Modèle rechargé depuis {latest_model.source}"}
