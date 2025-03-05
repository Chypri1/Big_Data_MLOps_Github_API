import json
import os
from dotenv import load_dotenv
from fastapi import FastAPI
import mlflow.pyfunc
from mlflow.tracking import MlflowClient
import pandas as pd
from pydantic import BaseModel
from threading import Lock
import numpy as np

# Charger les variables d'environnement
load_dotenv()
MODEL_NAME = os.getenv("MODEL_NAME")
URI_MLFLOW = os.getenv("URI_MLFLOW")
# Définir le client MLflow
mlflow.set_tracking_uri(URI_MLFLOW)
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

     # Obtenir les indices des 5 classes avec les plus grandes probabilités (triés par ordre décroissant)
    top_5_indices = np.argsort(predictions, axis=1)[:, -5:][:, ::-1]  # On prend les 5 derniers et on les inverse
    
    # Convertir ces indices en labels
    top_5_labels = [[labels[idx] for idx in sample] for sample in top_5_indices]
    
    # Récupérer les valeurs des probabilités associées aux 5 meilleures classes
    top_5_probas = [[predictions[i, idx] for idx in top_5_indices[i]] for i in range(len(predictions))]

    return {"top_5_predictions": top_5_labels, "top_5_probabilities": top_5_probas}
# 🔒 Verrou pour éviter plusieurs chargements simultanés
model_lock = Lock()

@app.post("/reload")
async def reload_model():
    global model, model_name, model_source
    with model_lock:
        model, model_name, model_source = load_model()
    return {"message": f"✅ Modèle rechargé depuis {model_source}"}
