from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
import pandas as pd
import joblib

class RandomForestModel:
    def __init__(self, lr=0.01, n_estimators=100):
        self.encoder = LabelEncoder()
        self.model = RandomForestClassifier(n_estimators=n_estimators)
        self.labels = None

    def train(self, X_train, y_train):
        self.model.fit(X_train, y_train)

    def predict(self, X):
        return self.model.predict(X)

    def save_model(self, path):
        joblib.dump(self.model, path)

    def load_model(self, path):
        self.model = joblib.load(path)
