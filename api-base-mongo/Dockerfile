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

# Installer python-dotenv pour charger les variables d’environnement
RUN pip install python-dotenv

# Exposer le port défini dans l’environnement
EXPOSE 8888

# Lancer l'application avec Uvicorn en chargeant le .env
CMD ["sh", "-c", "uvicorn --host 0.0.0.0 --port 8888 lib_mongoDB:app"]
