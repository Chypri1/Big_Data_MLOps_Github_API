# Utilisation de l'image Python officielle
FROM python:3.11-slim

# Définition du répertoire de travail
WORKDIR /app

# Copie des fichiers nécessaires
COPY . .

# Installation des dépendances
RUN pip install --no-cache-dir -r requirements.txt

# Exécution du script
CMD ["sh", "-c", "uvicorn --host 0.0.0.0 --port 3232 appelGithub:app"]
