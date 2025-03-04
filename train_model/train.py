import json
import requests
import mlflow
import mlflow.sklearn
import os
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import pandas as pd
from models.gradient_boosting import GradientBoostingModel
from models.random_forest import RandomForestModel
import numpy as np
from tqdm import tqdm  
from mlflow.tracking import MlflowClient
from fastapi import FastAPI


URI_API_BASE_MONGO_DB = "URI_API_BASE_MONGO_DB"

# Configuration MLflow
mlflow.set_tracking_uri("http://mlflow:8083")
client = MlflowClient()


def get_model(model_name, **kwargs):
    if model_name == "gradient_boosting":
        return GradientBoostingModel(**kwargs)
    elif model_name == "random_forest":
        return RandomForestModel(**kwargs)
    else:
        raise ValueError(f"Modèle {model_name} inconnu !")

def prepare_data(model, df, alpha, beta, gamma):
    """Prépare les données en encodant les labels."""
    df = df.dropna(subset=["language"])
    language = df["language"]
    df = df[df.columns[df.dtypes != "object"]]
    df["trend_score"] = (
        alpha * df["stargazers_count"] + 
        beta * df["forks_count"] + 
        gamma * df["watchers_count"]
    )
    df["language"] = model.encoder.fit_transform(language)
    model.labels = model.encoder.classes_
    return df

def train_log(df, model_name="gradient_boosting", epochs=10, alpha=2, beta=1, gamma=0.7, batch_size=32):
    """Entraîne le modèle avec mini-batches et log les résultats sur MLflow avec une barre de progression."""
    mlflow.set_experiment(f"Train {model_name}")
    model = get_model(model_name, lr=0.01, n_estimators=10)
    df = prepare_data(model, df, alpha, beta, gamma)
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

        for epoch in tqdm(range(1, epochs + 1), desc="📈 Entraînement des epochs"):
            print(f"\n🔄 Epoch {epoch}/{epochs}...")
            for X_batch, y_batch in zip(X_batches, y_batches):
                model.train(X_batch, y_batch)

            y_pred = model.predict(X_test)
            acc = accuracy_score(y_test, y_pred)

            mlflow.log_metric("accuracy", acc, step=epoch)
            print(f"🎯 Accuracy: {acc:.4f}")
 
        # Enregistrement du modèle et Ajout du modèle à Model Registry
        # Sauvegarde des labels dans un fichier JSON
        labels_path = f"{model_name}_labels.json"
        with open(labels_path, "w") as f:
            json.dump(model.labels.tolist(), f)

        # Log des labels en tant qu'artifact MLflow
        mlflow.log_artifact(labels_path, artifact_path="labels")
        mlflow.sklearn.log_model(model.model, artifact_path=f"{model_name}_model",registered_model_name=model_name)

        model_uri = f"runs:/{run.info.run_id}/{model_name}_model"

        model_version = client.create_model_version(name=model_name, source=model_uri, run_id=run.info.run_id)
        print(f"✅ Modèle {model_name} enregistré en version {model_version.version}")
        #Mise en production automatique du modèle
        client.transition_model_version_stage(
            name=model_name,
            version=model_version.version,
            stage="Production"
        )
        print(f"Modèle {model_name} version {model_version.version} mis en production sur MLflow Serving!")

        with open("./.env", "w") as env_file:
            env_file.write(f"MODEL_NAME={model_name}\n")

        print(f"Nouvelle variable MODEL_NAME={model_name} enregistrée dans .env")

    return acc


# Initialiser FastAPI
app = FastAPI()


@app.get("/train")
def train():
    # revoir ça 
    url = URI_API_BASE_MONGO_DB +"/count"
    count = requests.get(url=url)
    url = URI_API_BASE_MONGO_DB +"/show_data?page="+str(1)+"&page_size="+str(count)
    repositories = requests.get(url=url)
    
    df = pd.DataFrame(repositories['data'])
    acc = train_log(df,model_name="random_forest",epochs=10, batch_size=256)
    print(f"Modèle entraîné avec une accuracy de {acc}")