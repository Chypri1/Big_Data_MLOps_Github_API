# Utiliser une image officielle Python 3.11
FROM python:3.11-slim

# Définir le répertoire de travail
WORKDIR /app

# Copier les fichiers nécessaires
COPY requirements.txt .

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Copier le reste des fichiers de l'application
COPY . .

# Installer python-dotenv pour charger les variables d’environnement
RUN pip install python-dotenv

# Exposer le port de l’API
EXPOSE 80

CMD ["sh", "-c", "uvicorn --host 0.0.0.0 --port 80 appelGithub:app"]
