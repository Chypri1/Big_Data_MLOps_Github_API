import requests
import json
from dotenv import load_dotenv
import os
import string
import pickle
import time

 # Charger les variables d’environnement
load_dotenv()

# Variables d'environnement
BASE_URL = "https://api.github.com"
base_url = BASE_URL


API_KEY_GH = os.getenv("API_KEY_GH")
api_key = API_KEY_GH 



class AppelGithub:
    save_folder = f"./" # revoir si ça marche sur azure 
    
    def __init__(self):
        # TO_CHANGE
        pass
    
    def pickle_this(target, name, file_path=save_folder):
        path = file_path+name
        file = open(path, "wb")
        if file:
            pickle.dump(target, file)
            file.close()
            return True
        file.close()
        return False
        

    def unpickle_this(name, file_path=save_folder):
        path = file_path+name
        file = open(path, "rb")
        res = []
        if file:
            res = pickle.load(file)
            file.close()
            return res
        file.close()
        return res


    def get_call(paths, params=None, header=None):
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

    def get_repos_created_in_day_multipages(year, month="01", day="01", max_pages=0):
        # Recherche de repositories créés en 2024
        query = "created:"+str(year)+"-"+str(month)+"-"+str(day)
        params = {"q": query, "per-page": 30}
        header = {"Authorization": f"token {api_key}"}
        # Appeler l'API de recherche de repositories
        repos_data = get_call("search/repositories", params=params, header=header)
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
                repos_data = get_call("search/repositories", params=params, header=header)
                res.extend(repos_data.get("items", []))
                pickle_this(res, "repos_"+str(year)+"_"+str(month))
            
            return res
        else:
            return []
        
    def lancement_récup_auto():
                # ajout de la boucle pour que cela fonctionne chaque jour avec de la robustesse 
        max_pages=25
        months = ["01","02","03","04","05","06","07","08","09","10",11,12]
        res = {}

        for year in range(2010,2025):
            for month in months:
                for day in range (1,28):
                    res = get_repos_created_in_day_multipages(year, month=month, day=day if day>=10 else "0"+str(day), max_pages=max_pages)

        print(len(res))
