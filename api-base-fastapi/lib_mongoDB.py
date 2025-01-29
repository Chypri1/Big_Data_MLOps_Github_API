from pymongo import MongoClient
from fastapi import FastAPI, UploadFile
class BackForDatabase:
    # Informations de connexion à MongoDB
    """
    USERNAME = "username_mongoDB"
    PASSWORD = "password_mongoDB"
    DB_NAME = "my_database"
    COLLECTION_NAME = "my_collection"
    """

    def __init__(self, username = "username_mongoDB", password = "password_mongoDB", database = "my_database", collection_name = "my_collection"):
        self.username = username
        self.password = password
        self.database = database
        self.collection_name = collection_name

    def connect_to_mongo(self, host="localhost", port=27017):
        """
        Connexion à MongoDB et retour du client.
        """
        try:
            client = MongoClient(f"mongodb://{self.username}:{self.password}@{host}:{port}/")
            print("Connexion à MongoDB réussie.")
            return client
        except Exception as e:
            print(f"Erreur de connexion à MongoDB : {e}")
            return None

    def insert_documents(self, collection, documents):
        """
        Insère les documents dans la collection si ils n'existent pas déjà.
        """
        documents_to_insert = []
        for repo in documents:
            # Vérifie si le document existe déjà dans la collection
            if collection.count_documents({"name": repo["name"]}, limit=1) == 0:
                documents_to_insert.append(repo)
            else:
                print(f"Le document existe déjà : {repo['name']}")

        # Insère les nouveaux documents
        if documents_to_insert:
            result = collection.insert_many(documents_to_insert)
            print(f"Documents insérés avec les IDs : {result.inserted_ids}")
        else:
            print("Aucun document à insérer. Tous existent déjà.")

    def display_documents(self, collection):
        """
        Affiche tous les documents dans une collection MongoDB.
        """
        print("Données dans la collection :")
        for document in collection.find():
            print(document)

if __name__ == "__main__":
    # Client API pour la base 
    backForDatabase = BackForDatabase() # initialiser les valeurs si besoin plus tard
    app = FastAPI()


    @app.get("/hello_world")
    def hello_world():
        return {"message":"hello world"}

    # Connexion à MongoDB
    client = backForDatabase.connect_to_mongo()
    
    if client:
        print(" ça fonctionne !")



