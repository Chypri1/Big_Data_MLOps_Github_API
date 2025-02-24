import mlflow
import mlflow.sklearn
from models.model_factory import get_model
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
import pandas as pd

# Charger les données
repositories = [...]  # Charger tes données ici
model_name = "gradient_boosting"  # 🔥 Change ici pour tester d'autres modèles

# Charger le modèle depuis la factory
model = get_model(model_name, lr=0.01, n_estimators=100)
df = model.prepare_data(repositories)

X = df.drop(columns=["language"])
y = df["language"]
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, shuffle=True)

# Expérimentation MLflow
with mlflow.start_run():
    mlflow.log_param("model_name", model_name)
    
    model.train(X_train, y_train)
    y_pred = model.predict(X_test)

    mse = mean_squared_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)

    mlflow.log_metric("mse", mse)
    mlflow.log_metric("r2_score", r2)

    mlflow.sklearn.log_model(model.model, f"{model_name}_model")

    print(f"📉 MSE: {mse:.4f} | 📈 R² Score: {r2:.4f}")

# Sauvegarder le modèle localement
model.save_model(f"models/{model_name}.pkl")
