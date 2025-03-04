import pandas as pd
from sklearn.preprocessing import LabelEncoder
import numpy as np
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import mean_squared_error, r2_score
import joblib

class GradientBoostingModel():
    def __init__(self,lr=0.01, n_estimators=100):
        """Initialise le modèle et l'encodeur de labels."""
        self.encoder = LabelEncoder()
        self.model = GradientBoostingClassifier(n_estimators=n_estimators,learning_rate=lr, max_depth=5)
        self.label = None
        

    def train(self, X_train, y_train):
        self.model.fit(X_train, y_train)

    def predict(self, X):
        return self.model.predict(X)

    def save_model(self, path):
        joblib.dump(self.model, path)

    def load_model(self, path):
        self.model = joblib.load(path)
