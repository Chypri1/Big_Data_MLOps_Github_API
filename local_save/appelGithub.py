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
base_url = BASE_URL
URI_MONGO_DB = os.getenv("URI_MONGO_DB")


API_KEY_GH = os.getenv("API_KEY_GH")
api_key = API_KEY_GH 

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
    save_folder = f"./" # revoir si ça marche sur azure 
    
    def __init__(self):
        # TO_CHANGE
        pass

    def get_repos_created_in_day_multipages(self, year, month="01", day="01", max_pages=0):
        # Recherche de repositories créés en 2024
        query = "created:"+str(year)+"-"+str(month)+"-"+str(day)
        params = {"q": query, "per-page": 30}
        header = {"Authorization": f"token {api_key}"}
        # Appeler l'API de recherche de repositories
        repos_data = self.get_call("search/repositories", params=params, header=header)
        num_pages = 0
        res = []
        if repos_data:
            res.extend(repos_data.get("items", []))
            repo_pages = (repos_data.get("total_count", 0) // 30)
            print(repo_pages)
            if max_pages > 0:
                num_pages = min(max_pages, repo_pages)
            
            for ii in range(2, num_pages+1):
                repos_data={}
                params = {"q": query, "per-page": 30, "page": ii}
                repos_data = self.get_call("search/repositories", params=params, header=header)
                res.extend(repos_data.get("items", []))
                self.pickle_this(res, "repos_"+str(year)+"_"+str(month))
            
            return res
        else:
            return []
  
    def get_call(self, paths, params=None, header=None):
        url = f"{base_url}/{paths}"
        response = requests.get(url, params=params, headers=header)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 403:
            print("La patience est d'or. Enculé")
            time.sleep(61)
            response = requests.get(url, params=params, headers=header)
            return response.json()
        else:
            print(f"Error: {response.status_code} - {response.json().get('message', 'Unknown error')}")
            return {}
        
        
    def pickle_this(self, target, name, file_path=save_folder):
        path = file_path+name
        file = open(path, "wb")
        if file:
            pickle.dump(target, file)
            file.close()
            return True
        file.close()
        return False
        

    def unpickle_this(self, name, file_path=save_folder):
        path = file_path+name
        file = open(path, "rb")
        res = []
        if file:
            res = pickle.load(file)
            file.close()
            return res
        file.close()
        return res
  
  
  

# 🎯 Création de l'API FastAPI
client = AppelGithub() 

max_pages=25
months = ["01","02","03","04","05","06","07","08","09","10",11,12]
res = {}

for year in range(2010,2025,1):
    for month in months:
        for day in range (1,29,1):
            res = client.get_repos_created_in_day_multipages(year, month=month, day=(day if day>=10 else "0"+str(day)), max_pages=max_pages)
            requests.post(URI_MONGO_DB + "/add_data",json = res)
    print(len(res))


app = FastAPI()  

@app.get("/")
def base():
    return {}

@app.get("/hello_world")
def hello_world():
    return {"message": "Hello, world!"}

@app.get("/jour_récup_auto")
def jour_récup_auto():
    return {"message":""+"day: " +str(day) + "month: " + str(month) + "year: " + str(year)}