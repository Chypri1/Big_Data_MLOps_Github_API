import requests
from dotenv import load_dotenv
import os
import pickle
import time
from fastapi import FastAPI
from pydantic import BaseModel

# Charger les variables d’environnement
load_dotenv()

# Variables d'environnement
BASE_URL = "https://api.github.com"
URI_MONGO_DB = os.getenv("URI_MONGO_DB")
API_KEY_GH = os.getenv("API_KEY_GH")


class OwnerModel(BaseModel):
    login: str
    id: int
    html_url: str


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
        return []

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

    def pickle_this(self, target, name, file_path=save_folder):
        path = os.path.join(file_path, name)
        with open(path, "wb") as file:
            pickle.dump(target, file)

    def unpickle_this(self, name, file_path=save_folder):
        path = os.path.join(file_path, name)
        with open(path, "rb") as file:
            return pickle.load(file)


# 🎯 API FastAPI
app = FastAPI()
client = AppelGithub()




@app.get("/")
def base():
    return {"message": "Bienvenue sur l'API GitHub"}


@app.get("/hello_world")
def hello_world():
    return {"message": "Hello, world!"}


@app.get("/jour_récup_auto")
def jour_récup_auto(year: int, month: str, day: int):
    return {"message": f"Day: {day}, Month: {month}, Year: {year}"}


from concurrent.futures import ThreadPoolExecutor
import logging

# Configurer les logs pour voir ce qu'il se passe en arrière-plan
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

executor = ThreadPoolExecutor(max_workers=1)

@app.get("/start")
def start_recup_auto():
    future = executor.submit(recup_auto)

    if future.running():
        return {"message": "Récupération déjà en cours."}
    else:
        return {"message": "Récupération démarrée en arrière-plan."}

def recup_auto():
    try:
        logger.info("Démarrage de la récupération...")
        max_pages = 25
        months = [f"{i:02d}" for i in range(4, 13)]
        res = []
        year = 2024
        #for year in range(2010, 2025):
        for month in months:
            for day in range(1, 29):
                day_str = f"{day:02d}"
                repos = client.get_repos_created_in_day_multipages(year, month, day_str, max_pages)

                if URI_MONGO_DB:
                    response = requests.post(f"{URI_MONGO_DB}/add_data", json=repos)
                    logger.info(f"POST vers MongoDB: {response.status_code}")

                res.extend(repos)

        logger.info("Récupération terminée avec succès !")

    except Exception as e:
        logger.error(f"Erreur dans la récupération : {e}")


