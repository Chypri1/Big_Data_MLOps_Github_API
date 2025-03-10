import json
import requests
import mlflow
import mlflow.sklearn
import os
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score
import pandas as pd
from models.gradient_boosting import GradientBoostingModel
from models.random_forest import RandomForestModel
import numpy as np
from tqdm import tqdm  
from mlflow.tracking import MlflowClient
from fastapi import FastAPI
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import Optional, Dict

# Charger les variables d'environnement
load_dotenv()

URI_MLFLOW = os.getenv("URI_MLFLOW")

# Configuration MLflow
mlflow.set_tracking_uri(URI_MLFLOW)
client = MlflowClient()


def get_model(model_name, **kwargs):
    """Récupère le modèle"""
    if model_name == "gradient_boosting":
        return GradientBoostingModel(**kwargs)
    elif model_name == "random_forest":
        return RandomForestModel(**kwargs)
    else:
        raise ValueError(f"Modèle {model_name} inconnu !")

def prepare_data(model, df):
    """Prépare les données en encodant la date et les indicateurs d'utilisation."""
    # Supprimer les lignes sans langage
    df = df.dropna(subset=["language"])
    df = df.dropna(subset=['created_at'])
    df['created_at'] = pd.to_datetime(df['created_at'])
    df['year'] = df['created_at'].dt.year
    df['month'] = df['created_at'].dt.month
    df['week'] = df['created_at'].dt.isocalendar().week
    df['day'] = df['created_at'].dt.day
    df = df.groupby(['year', 'month', 'week', 'day', 'language']).agg(
        number_repos=('name', 'count'),
        mean_fork=('forks_count', 'mean'),
        mean_watched=('watchers_count', 'mean'),
        mean_star=('stargazers_count', 'mean')
    ).reset_index()
    df['var_repos'] = df.groupby('language')['number_repos'].diff().fillna(0)
    # Encodage du langage
    df["language"] = model.encoder.fit_transform(df["language"])
    model.labels = model.encoder.classes_
    return df


def train_log(df, model_name="gradient_boosting", epochs=10, batch_size=32, lr=0.01, n_estimators=10):
    """Entraîne le modèle avec mini-batches et log les résultats sur MLflow avec une barre de progression."""
    mlflow.set_experiment(f"Train {model_name}")
    model = get_model(model_name, lr=lr, n_estimators=n_estimators)
    df = prepare_data(model, df)
    X = df.drop(columns=["language"])
    y = df["language"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, shuffle=True)
    num_batches = int(np.ceil(len(X_train) / batch_size))
    X_batches = [X_train[i * batch_size:(i + 1) * batch_size] for i in range(num_batches)]
    y_batches = [y_train[i * batch_size:(i + 1) * batch_size] for i in range(num_batches)]

    X_batches = [batch for batch in X_batches if len(batch) > 0]
    y_batches = [batch for batch in y_batches if len(batch) > 0]

    with mlflow.start_run() as run:
        mlflow.log_param("model_name", model_name)
        mlflow.log_param("epochs", epochs)
        mlflow.log_param("batch_size", batch_size)

        for epoch in tqdm(range(1, epochs + 1), desc="Entraînement des epochs"):
            print(f"\nEpoch {epoch}/{epochs}...")
            for X_batch, y_batch in zip(X_batches, y_batches):
                model.train(X_batch, y_batch)

            y_pred = model.predict(X_test)
            acc = accuracy_score(y_test, y_pred)
            mlflow.log_metric("accuracy", acc, step=epoch)
            print(f"Accuracy: {acc:.4f}")

            f1 = f1_score(y_test, y_pred, average='weighted')
            mlflow.log_metric("f1_score", f1, step=epoch)
            print(f"FSCORE = {f1}")
 
        # Enregistrement du modèle et Ajout du modèle à Model Registry
        artifact_path = f"{model_name}_model"

        # Sauvegarde des labels en tant qu'artefact 
        mlflow.log_dict({"labels": model.labels.tolist()}, artifact_file=f"{artifact_path}/labels.json")

        # Enregistrement du modèle
        mlflow.sklearn.log_model(model.model, artifact_path=artifact_path, registered_model_name=model_name)

        # Récupérer la version du modèle
        model_versions = client.search_model_versions(f"name='{model_name}'")
        latest_version = max([int(v.version) for v in model_versions])


    return acc, latest_version

# Initialise FastAPI
app = FastAPI()


class InputData(BaseModel):
    model_name: str
    data: list
    epochs: int
    batch_size: int
    metrics: Optional[Dict[str, float]] = {"lr": 0.01, "n_estimators": 100}

@app.post("/train")
def train(inputData: InputData):
    """Entraine le modèle choisi avec les données
    Renvoie le nom du modèle, sa version et son accuracy
    """
    model_name, epochs, batch_size, metrics, data = (
        inputData.model_name,
        inputData.epochs,
        inputData.batch_size,
        inputData.metrics if inputData.metrics else {"lr": 0.01, "n_estimators": 100},
        inputData.data,
    )
    df = pd.DataFrame(data)
    acc, version = train_log(
        df,
        model_name=model_name,
        epochs=epochs,
        batch_size=batch_size,
        lr=metrics['lr'],
        n_estimators=int(metrics["n_estimators"])
    )

    return model_name,version, acc

@app.post("/model-stage")
def change_staging(model_name: str, version: str, stage: str):
    """Change le stage de la version du modèle donnée en paramètre"""
    try:
        client.transition_model_version_stage(
            name=model_name,
            version=version,
            stage=stage
        )
        return {"message": f"Modèle {model_name} version {version} en staging {stage}."}
    except Exception as e:
        return {"error": f"Une erreur s'est produite lors du changement de staging : {str(e)}"}
