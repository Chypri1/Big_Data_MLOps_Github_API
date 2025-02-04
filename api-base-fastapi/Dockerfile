# Utiliser une image officielle Python 3.11 comme base
FROM python:3.11-slim

# Définir le répertoire de travail dans le conteneur
WORKDIR /app

# Copier les fichiers nécessaires dans le conteneur
COPY requirements.txt .

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Copier le reste des fichiers de l'application
COPY . .

# Exposer le port 8888
EXPOSE 8888

# Lancer l'application avec Uvicorn
CMD ["uvicorn", "--host", "0.0.0.0", "--port", "8888", "lib_mongoDB:app"]
