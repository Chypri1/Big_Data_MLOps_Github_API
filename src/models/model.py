import pandas as pd
from sklearn.preprocessing import LabelEncoder
import numpy as np
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_squared_error, r2_score


class ModelTrainer():
    def __init__(self,repositories,lr=0.01):
        """Initialise le modèle et l'encodeur de labels."""
        self.encoder = LabelEncoder()
        self.model = GradientBoostingRegressor(n_estimators=1000, learning_rate=lr, max_depth=5, warm_start=True)
        self.labels = None  # Stockera les noms des langages encodés
        df = pd.DataFrame(repositories)
        df = df.dropna(subset=["language"])
        language = df["language"]
        df = df[df.columns[df.dtypes != "object"]]

        # Encodage de la colonne "language"
        df["language"] = self.encoder.fit_transform(language)
        self.labels = self.encoder.classes_
        self.df = df
        

    def train(self,epochs=10):
        # Séparation des données
        X = self.df.drop(columns=["language"])
        y = self.df["language"]

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3,shuffle=True)

        mse_history = []  # Stocker l'évolution du MSE
        r2_history = []  # Stocker l'évolution du R²
        
        for epoch in range(1, epochs + 1):
            print(f"\n🔄 Epoch {epoch}/{epochs}...")
            
            # Ajuster le modèle
            self.model.n_estimators += 10  # Ajouter 10 arbres par epoch
            self.model.fit(X_train, y_train)

            # Prédictions
            y_pred = self.model.predict(X_test)

            # Calcul des métriques
            mse = mean_squared_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)

            mse_history.append(mse)
            r2_history.append(r2)

            print(f"📉 MSE: {mse:.4f} | 📈 R² Score: {r2:.4f}")

        # Affichage de l'évolution des performances
        self.plot_training_curve(mse_history, r2_history)
        # self.plot_pred_true(y_test,y_pred)

    def plot_training_curve(self, mse_history, r2_history):
        """Affiche l'évolution du MSE et du R² Score au fil des epochs"""
        plt.figure(figsize=(12, 5))

        plt.subplot(1, 2, 1)
        plt.plot(range(1, len(mse_history) + 1), mse_history, marker='o', color='r')
        plt.xlabel("Epochs")
        plt.ylabel("MSE")
        plt.title("Évolution du Mean Squared Error")

        plt.subplot(1, 2, 2)
        plt.plot(range(1, len(r2_history) + 1), r2_history, marker='s', color='b')
        plt.xlabel("Epochs")
        plt.ylabel("R² Score")
        plt.title("Évolution du R² Score")

        plt.tight_layout()
        plt.show()

    def prepare_data(self, repositories):
        df = pd.DataFrame(repositories).dropna(subset=["language"])
        language = df["language"]
        df = df[df.columns[df.dtypes != "object"]]
        df["language"] = self.encoder.fit_transform(language)
        self.labels = self.encoder.classes_
        return df

    def train(self, X_train, y_train):
        self.model.fit(X_train, y_train)

    def predict(self, X):
        return self.model.predict(X)

    def save_model(self, path):
        joblib.dump(self.model, path)

    def load_model(self, path):
        self.model = joblib.load(path)
