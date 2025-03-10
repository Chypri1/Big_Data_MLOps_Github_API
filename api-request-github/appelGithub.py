import requests
from dotenv import load_dotenv
import os
import pickle
import time
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from confluent_kafka import Producer
import json
from concurrent.futures import ThreadPoolExecutor
import logging

# Charger les variables d’environnement
load_dotenv()

BASE_URL = "https://api.github.com"
URI_MONGO_DB = os.getenv("URI_API_BASE_MONGO_DB")
API_KEY_GH = os.getenv("API_KEY_GH")
KAFKA_BROKER = os.getenv("KAFKA_BROKER")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC")
ENV = os.getenv("ENV")

# Modèle de données d'un propriétaire de repo
class OwnerModel(BaseModel):
    login: str
    id: int
    html_url: str

# Modèle de données d'un repo
class DocumentModel(BaseModel):
    id: int
    node_id: str
    name: str
    full_name: str
    private: bool
    owner: OwnerModel
    html_url: str
    description: str | None
    fork: bool
    created_at: str
    updated_at: str
    pushed_at: str
    language: str | None
    forks_count: int
    stargazers_count: int
    watchers_count: int
    open_issues_count: int


class AppelGithub:
    save_folder = "./"

    def __init__(self, base_url=BASE_URL, uri_mongo_db=URI_MONGO_DB, api_key=API_KEY_GH):
        self.base_url = base_url
        self.uri_mongo_db = uri_mongo_db
        self.api_key = api_key

    ''' Récupérer les répo pour une date donnée
        - IN:
            self: la classe AppelGithub
            year: année de création, paramètre obligatoire
            month: numéro du mois en format double digit
            day: numéro du jour en format double digit
            max_pages: nombre maximum de pages à récupérer, 0 = pas de limite
        
        - OUT:
            Liste de repos, vide si introuvable
    '''
    def get_repos_created_in_day_multipages(self, year, month="01", day="01", max_pages=0):
        query = f"created:{year}-{month}-{day}"
        params = {"q": query, "per-page": 30}
        header = {"Authorization": f"token {self.api_key}"}
        repos_data = self.get_call("search/repositories", params=params, header=header)
        res = []

        if repos_data:
            res.extend(repos_data.get("items", []))
            repo_pages = repos_data.get("total_count", 0) // 30
            num_pages = min(max_pages, repo_pages) if max_pages > 0 else repo_pages

            for ii in range(2, num_pages + 1):
                params["page"] = ii
                repos_data = self.get_call("search/repositories", params=params, header=header)
                res.extend(repos_data.get("items", []))
                self.pickle_this(res, f"repos_{year}_{month}")

        return res

    # Appelle l'api github et retourne la réponse si elle est positive. 
    # Cette méthode génère de l'attente active en attendant dans le cas où nous aurions dépassé notre taux de requetage 
    def get_call(self, paths, params=None, header=None):
        url = f"{self.base_url}/{paths}"
        response = requests.get(url, params=params, headers=header)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 403:
            print("Attente avant nouvel essai...")
            time.sleep(61)
            response = requests.get(url, params=params, headers=header)
            return response.json()
        else:
            print(f"Erreur {response.status_code}: {response.json().get('message', 'Erreur inconnue')}")
            return {}

    # Une paire de méthodes pour encapsuler des appels à pickles et les ouvertures/fermetures de fichiers qui vont avec
    def pickle_this(self, target, name, file_path=save_folder):
        path = os.path.join(file_path, name)
        with open(path, "wb") as file:
            pickle.dump(target, file)

    def unpickle_this(self, name, file_path=save_folder):
        path = os.path.join(file_path, name)
        with open(path, "rb") as file:
            return pickle.load(file)


client = AppelGithub()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# API pour intéragir avec les composants
app = FastAPI()

# Endpoints
@app.get("/")
def base():
    return {"message": "Bienvenue sur l'API GitHub"}


@app.get("/hello_world")
def hello_world():
    return {"message": "Hello, world!"}

@app.post("/recup_jour")
def jour_récup_auto(year: int, month: int, day: int):
    return send_to_kafka(year, month, day)

@app.get("/start")
def start_recup_auto():
    return send_to_threading

# Les méthodes ci-dessous permettent l'ingestion automatique par multithreading
executor = ThreadPoolExecutor(max_workers=1)

# Execution d'un thread
def send_to_threading():
    future = executor.submit(recup_auto)

    if future.running():
        return {"message": "Récupération déjà en cours."}
    else:
        return {"message": "Récupération démarrée en arrière-plan."}

# Ingestion automatique par multithreading
def recup_auto():
    try:
        logger.info("Démarrage de la récupération...")
        max_pages = 25
        months = [f"{i:02d}" for i in range(1, 13)]
        res = []
        year = 2024
        # Récupérer 25 pages de 30 répos pour chaque jour de 2010 à 2024
        for year in range(2024, 2010):
            for month in months:
                for day in range(1, 29):
                    day_str = f"{day:02d}"
                    repos = client.get_repos_created_in_day_multipages(year, month, day_str, max_pages)

                    if URI_MONGO_DB:
                        # option 1 with call to kafka queue (for local deployement)
                        if(ENV == "LOCAL"):
                            for doc in repos:
                                message = json.dumps(doc)  # Convertir en JSON
                                producer.produce(KAFKA_TOPIC, key=str(doc.id), value=message, callback=delivery_report)
                            producer.flush()

                        # option 2 with direct call to api-base-mongo (for azure deployement)
                        else:
                            response = requests.post(f"{URI_MONGO_DB}/add_data", json=repos)
                            logger.info(f"POST vers MongoDB: {response.status_code}")

                    res.extend(repos)

        logger.info("Récupération terminée avec succès !")

    except Exception as e:
        logger.error(f"Erreur dans la récupération : {e}")


# Fonction pour connaitre l'état du message
def delivery_report(err, msg):
    """Callback pour savoir si le message a été envoyé avec succès"""
    if err is not None:
        print(f"Erreur d'envoi Kafka: {err}")
    else:
        return (f"Message envoyé à {msg.topic()} [{msg.partition()}] avec offset {msg.offset()}")


# Envoyer à kafka
conf = {
    "bootstrap.servers": KAFKA_BROKER,
    "security.protocol": "PLAINTEXT",
    "client.id": "python-producer"
}
producer = Producer(conf)

def send_to_kafka(year, month, day):
    try:
        month_str = f"{month:02d}"
        day_str = f"{day:02d}"
        repos = client.get_repos_created_in_day_multipages(str(year), month_str, day_str, 1)

        if URI_MONGO_DB:
            for doc in repos:
                    # Conversion du dictionnaire en objet DocumentModel
                    document = DocumentModel(**doc)
                    # Sérialisation en JSON
                    message = document.json()  
                    # Envoi à Kafka
                    producer.produce(KAFKA_TOPIC, key=str(document.id), value=message, callback=delivery_report)
                
            producer.flush()
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur serveur : {str(e)}")
