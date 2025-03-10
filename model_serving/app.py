import json
import os
from typing import Optional
from dotenv import load_dotenv
from fastapi import FastAPI
import mlflow.pyfunc
from mlflow.tracking import MlflowClient
import pandas as pd
from pydantic import BaseModel
from threading import Lock
import numpy as np
from collections import defaultdict
from sklearn.preprocessing import LabelEncoder

# Charger les variables d'environnement
load_dotenv()
mlflow.set_tracking_uri(os.getenv("URI_MLFLOW"))
client = MlflowClient()

# Fonction pour charger le modèle et ses labels
def load_model(name="gradient_boosting", version=None):
    model_version = client.get_model_version(name, str(version)) if version else client.get_latest_versions(name, stages=["Production"])[0]
    model = mlflow.sklearn.load_model(model_version.source)
    
    # Charger les labels depuis l'artefact
    try:
        labels_path = mlflow.artifacts.download_artifacts(f"{model_version.source}/labels.json")
        with open(labels_path, "r") as f:
            labels = json.load(f)["labels"]
    except Exception:
        labels = None
    
    return model, labels

app = FastAPI()
model_lock = Lock()

# Préparer les données
def prepare_data(df):
    df = pd.DataFrame(df).dropna(subset=["language", "created_at"])
    df["created_at"] = pd.to_datetime(df["created_at"])
    df["year"], df["month"], df["week"], df["day"] = df["created_at"].dt.year, df["created_at"].dt.month, df["created_at"].dt.isocalendar().week, df["created_at"].dt.day

    df = df.groupby(["year", "month", "week", "day", "language"]).agg(
        number_repos=("name", "count"),
        mean_fork=("forks_count", "mean"),
        mean_watched=("watchers_count", "mean"),
        mean_star=("stargazers_count", "mean")
    ).reset_index()

    df["var_repos"] = df.groupby("language")["number_repos"].diff().fillna(0)

    return df.drop(columns=["language"])

class InputData(BaseModel):
    model_name: str
    model_version: Optional[str] = None
    data: list

# Endpoint de prédiction
@app.post("/predict")
async def predict(input_data: InputData):
    model_name, model_version, data = (
        input_data.model_name,
        input_data.model_version if input_data.model_version else None,
        input_data.data
    )
    with model_lock:
        model, labels = load_model(model_name, model_version)
    data = prepare_data(data)
    predictions = model.predict_proba(data)

    # Récupération du top 5 par repo
    top_5_indices = np.argsort(predictions, axis=1)[:, -5:][:, ::-1]
    top_5_labels = [[labels[idx] for idx in sample] for sample in top_5_indices]
    top_5_probas = [[predictions[i, idx] for idx in sample] for i, sample in enumerate(top_5_indices)]

    # Agrégation pour un top 5 global
    global_probs = defaultdict(float)
    for preds, probs in zip(top_5_labels, top_5_probas):
        for lang, prob in zip(preds, probs):
            global_probs[lang] += prob

    top_5_global = sorted(global_probs.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        "top 5 des langages qui croissent le plus": [
            {"langage": lang, "probabilité": prob} for lang, prob in top_5_global
        ]
    }