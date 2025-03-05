import json
import os
from dotenv import load_dotenv
from fastapi import FastAPI
import mlflow.pyfunc
from mlflow.tracking import MlflowClient
import pandas as pd
from pydantic import BaseModel
from threading import Lock

# Charger les variables d'environnement
load_dotenv()

# Définir le client MLflow
mlflow.set_tracking_uri("http://train_model:8083")
client = MlflowClient()

# Fonction pour récupérer le modèle
def load_model():
    model_name = os.getenv("MODEL_NAME")
    if not model_name:
        raise ValueError("❌ La variable d'environnement MODEL_NAME est introuvable dans .env")

    stage = "Production"
    latest_model = client.get_latest_versions(model_name, stages=[stage])[0]
    model = mlflow.sklearn.load_model(latest_model.source)
    print(f"✅ Modèle chargé depuis {latest_model.source}")
    return model, model_name, latest_model.source

# Charger initialement le modèle
model, model_name, model_source = load_model()

# Charger les labels associés
labels_path = f"./{model_name}_labels.json"
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
    predictions = model.predict_proba(df)  # Faire une prédiction standard

    # Obtenir les indices des classes avec la probabilité la plus élevée
    predicted_classes = predictions.argmax(axis=1)  # axis=1 pour chaque ligne (chaque échantillon)
    print("VASY",predicted_classes)
    # Convertir les indices en labels
    language_predictions = [labels[idx] for idx in predicted_classes]
    
    return {"predictions": predictions.tolist(), "language": language_predictions}

# 🔒 Verrou pour éviter plusieurs chargements simultanés
model_lock = Lock()

@app.post("/reload")
async def reload_model():
    global model, model_name, model_source
    with model_lock:
        model, model_name, model_source = load_model()
    return {"message": f"✅ Modèle rechargé depuis {model_source}"}
