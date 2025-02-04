from pymongo import MongoClient
from fastapi import FastAPI, HTTPException
from typing import List
from pydantic import BaseModel

PASSWORD_MONGO_URI = "TO_CHANGE"

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

class BackForDatabase:
    def __init__(self, connection_uri, database_name="my_database", collection_name="my_collection"):
        self.connection_uri = connection_uri
        self.database_name = database_name
        self.collection_name = collection_name
        self.client = None
        self.db = None
        self.collection = None

    def connect_to_mongo(self):
        """ Connexion à MongoDB (Azure Cosmos DB API Mongo) """
        try:
            self.client = MongoClient(self.connection_uri)
            self.db = self.client[self.database_name]
            self.collection = self.db[self.collection_name]
            
            if self.collection is not None:
                print("✅ Connexion réussie à MongoDB Cosmos DB")
            else:
                print("🚨 Erreur : Collection introuvable")
        except Exception as e:
            print(f"❌ Erreur de connexion : {e}")
            self.client = None  # Reset pour éviter des bugs plus tard

    def insert_documents(self, documents: List[dict]):
        """ Insère plusieurs documents dans MongoDB """
        if self.collection is None:
            print("🚨 Erreur : Collection non initialisée.")
            return {"error": "Collection non initialisée"}

        try:
            existing_names = {doc["name"] for doc in self.collection.find({}, {"name": 1})}
            documents_to_insert = [doc for doc in documents if doc["name"] not in existing_names]

            if documents_to_insert:
                result = self.collection.insert_many(documents_to_insert)
                return {"inserted_ids": result.inserted_ids}
            
            return {"message": "Aucun nouveau document à insérer."}
        except Exception as e:
            print(f"❌ Erreur lors de l'insertion : {e}")
            return {"error": str(e)}

    def display_documents(self):
        """ Retourne tous les documents de la collection """
        if self.collection is None:
            return {"error": "Collection non initialisée"}
        
        return list(self.collection.find({}, {"_id": 0}))  # Exclure `_id` pour simplifier

# 🎯 Initialisation avec l'URI Azure Cosmos DB
MONGO_URI = "mongodb+srv://cyprien16112001mpt:<password>@cluster-projet-mlops-big-data-mpt.global.mongocluster.cosmos.azure.com/?tls=true&authMechanism=SCRAM-SHA-256&retrywrites=false&maxIdleTimeMS=120000"
MONGO_URI = MONGO_URI.replace("<password>", PASSWORD_MONGO_URI)
backForDatabase = BackForDatabase(connection_uri=MONGO_URI)
backForDatabase.connect_to_mongo()

# 🎯 Création de l'API FastAPI
app = FastAPI()

@app.get("/")
def base():
    return {"message": "Client connecté !" if backForDatabase.client else "Client non connecté !"}

@app.get("/hello_world")
def hello_world():
    return {"message": "Hello, world!"}

@app.post("/add_data")
def add_data(documents: List[DocumentModel]):
    if backForDatabase.client is None:
        raise HTTPException(status_code=500, detail="Base de données non connectée")
    
    inserted_data = backForDatabase.insert_documents([doc.dict() for doc in documents])
    return {"message": "Données insérées", "data": inserted_data}

@app.get("/show_data")
def show_data():
    """ Afficher les données de la base MongoDB """
    return backForDatabase.display_documents()
