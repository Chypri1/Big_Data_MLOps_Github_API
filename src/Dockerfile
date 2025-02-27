# Utiliser une image Python légère
FROM python:3.9-slim

# Définir le répertoire de travail
WORKDIR /app

# Copier les fichiers nécessaires
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN apt update && apt install curl -y
# Copier le code source de l'API
COPY . .

# Exposer le port utilisé par FastAPI
EXPOSE 8000

# Lancer l'API avec Uvicorn
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8084"]
