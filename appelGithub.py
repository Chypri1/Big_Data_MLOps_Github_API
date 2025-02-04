import requests
import json

class AppelGithub:
    BASE_URL = "https://api.github.com"
    
    def __init__(self, api_key_file="api.json"):
        """
        Initialise l'objet avec la clé API chargée depuis un fichier JSON.
        """
        self.api_key = self.load_api_key(api_key_file)
        if not self.api_key:
            raise ValueError("Clé API GitHub non trouvée. Vérifiez le fichier ou la configuration.")

    @staticmethod
    def load_api_key(filepath):
        """
        Charge la clé API depuis un fichier JSON.
        """
        try:
            with open(filepath, 'r') as file:
                return json.load(file)["GH_API_KEY"]
        except FileNotFoundError:
            print(f"Erreur : Le fichier '{filepath}' est introuvable.")
            return None
        except KeyError:
            print("Erreur : Clé 'GH_API_KEY' introuvable dans le fichier JSON.")
            return None

    def get_call(self, path, params=None):
        """
        Effectue une requête GET à l'API GitHub.
        """
        url = f"{self.BASE_URL}/{path}"
        headers = {"Authorization": f"token {self.api_key}"}
        try:
            response = requests.get(url, params=params, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as err:
            print(f"Erreur HTTP : {err.response.status_code} - {response.json().get('message', 'Erreur inconnue')}")
        except Exception as e:
            print(f"Erreur : {e}")
        return None

    def get_repos_created_in_year(self, year, month_start='01', month_end='12', day_start='01', day_end='31'):
        """
        Récupère les repositories créés dans une année donnée.
        """
        query = f"created:>={year}-{month_start}-{day_start} created:<={year}-{month_end}-{day_end}"
        params = {"q": query}
        repos_data = self.get_call("search/repositories", params=params)
        if repos_data:
            return repos_data.get("items", [])
        else:
            return []

    def get_languages_from_repositories(self, repositories):
        """
        Extrait la liste des langages utilisés dans une liste de repositories.
        """
        return {repo["language"] for repo in repositories if repo["language"]}

    def print_languages_from_repositories(self, repositories):
        """
        Affiche les langages utilisés dans une liste de repositories.
        """
        languages = self.get_languages_from_repositories(repositories)
        if languages:
            print("Langages utilisés dans les repositories :")
            for language in sorted(languages):
                print(f"- {language}")
        else:
            print("Aucun langage trouvé dans les repositories.")


# Point d'entrée principal
if __name__ == "__main__":
    try:
        github_api = AppelGithub()

        # Récupérer les repositories créés en 2023
        print("Récupération des repositories créés en 2023...")
        repositories = github_api.get_repos_created_in_year(year=2023)

        if repositories:
            print(f"{len(repositories)} repositories trouvés.")
            print("Exemple d'un repository :", repositories[0])
            github_api.print_languages_from_repositories(repositories)
        else:
            print("Aucun repository trouvé pour l'année spécifiée.")
    except ValueError as e:
        print(e)
