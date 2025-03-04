from fastapi import FastAPI, HTTPException
from sklearn.metrics import accuracy_score
import mlflow
import numpy as np
import mlflow.sklearn

app = FastAPI()

# Charger le modèle au démarrage de l'API
MODEL_NAME = "gradient_boosting"  # Remplace par ton modèle
MODEL_VERSION = "1"  # À changer si nécessaire

try:
    model_uri = f"models:/{MODEL_NAME}/{MODEL_VERSION}"
    model = mlflow.sklearn.load_model(model_uri)
    print(f"✅ Modèle {MODEL_NAME} version {MODEL_VERSION} chargé avec succès.")
except Exception as e:
    print(f"❌ Erreur lors du chargement du modèle: {e}")
    model = None  # Empêche une erreur fatale

@app.post("/predict/")
def predict(data: dict):
    if model is None:
        raise HTTPException(status_code=500, detail="Modèle non chargé.")

    try:
        features = np.array(data["features"]).reshape(1, -1)
        prediction = model.predict(features)

        # Supposons qu'on récupère la vraie valeur (dans un cas réel, c'est plus complexe)
        true_label = data.get("language", None)
        acc = None

        if true_label is not None:
            acc = accuracy_score([true_label], prediction)
            mlflow.log_metric("accuracy_production", acc)  # Log de la métrique en production

        return {"prediction": prediction.tolist(), "accuracy": acc}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la prédiction: {e}")
