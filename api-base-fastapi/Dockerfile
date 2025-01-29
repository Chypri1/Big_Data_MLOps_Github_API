# Utiliser une image officielle Python 3.11 comme base
FROM python:3.11-slim

# Copier les fichiers nécessaires dans le conteneur
COPY requirements.txt ./

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Commande pour exécuter l'application après vérification que MongoDB est prêt
CMD ["lib/script_mongo.py"]
