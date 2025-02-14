from pymongo import MongoClient
from fastapi import FastAPI, HTTPException
from typing import List
from pydantic import BaseModel
from datetime import datetime
import os 
import logging
from dotenv import load_dotenv
from typing import Optional

# Charger les variables d’environnement
load_dotenv()

PASSWORD_MONGO_URI = os.getenv("PASSWORD_MONGO_URI")

class OwnerModel(BaseModel):
    login: str
    id: int
    html_url: str

from datetime import datetime
from pydantic import BaseModel

class OwnerModel(BaseModel):
    # Ajoute ici les champs nécessaires pour OwnerModel
    pass

class DocumentModel(BaseModel):
    id: int
    node_id: str
    name: str
    full_name: str
    private: bool
    owner: OwnerModel
    html_url: str
    description: Optional[str] = None
    fork: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    pushed_at: Optional[datetime] = None
    language: Optional[str] = None
    forks_count: int
    stargazers_count: int
    watchers_count: int
    open_issues_count: int
    
class DataIngestionDate (BaseModel):
    id: int
    node_id: str
    ingestion_date: str = datetime.utcnow().isoformat()

class BackForDatabase:
    def __init__(self, connection_uri, database_name="my_database", collection_name="my_collection", collection_data_ingestion_name = "my_ingestion_data_collection"):
        self.connection_uri = connection_uri
        self.database_name = database_name
        self.collection_name = collection_name
        self.collection_data_ingestion_name = collection_data_ingestion_name
        self.client = None
        self.db = None
        self.collection = None
        self.collection_data_ingestion = None

    def connect_to_mongo(self):
        """ Connexion à MongoDB (Azure Cosmos DB API Mongo) """
        try:
            self.client = MongoClient(self.connection_uri)
            self.db = self.client[self.database_name]
            self.collection = self.db[self.collection_name]
            self.collection_data_ingestion = self.db[self.collection_data_ingestion_name]
            
            if self.collection is not None:
                print("✅ Connexion réussie à MongoDB Cosmos DB")
            else:
                print("🚨 Erreur : Collection introuvable")
        except Exception as e:
            print(f"❌ Erreur de connexion : {e}")
            self.client = None  # Reset pour éviter des bugs plus tard

    from pymongo.errors import PyMongoError

    def insert_documents(self, documents: List[dict]):
        """ Insère plusieurs documents dans MongoDB et gère les erreurs de format de date """
        if self.collection is None or self.collection_name not in self.db.list_collection_names():
            print(f"⚠️ Collection '{self.collection_name}' absente. Création en cours...")
            self.collection = self.db[self.collection_name]  # Réassignation de la collection
            print(f"✅ Collection '{self.collection_name}' créée avec succès.")

        try:
            # Vérifier les noms déjà existants pour éviter les doublons
            existing_names = {doc["name"] for doc in self.collection.find({}, {"name": 1})}
            documents_to_insert = []

            for doc in documents:
                # Vérifier si le document existe déjà
                if doc["name"] in existing_names:
                    print(f"⚠️ Le document '{doc['name']}' existe déjà, il ne sera pas inséré.")
                    continue

                # Vérifier et convertir les dates (created_at, updated_at, pushed_at)
                for field in ["created_at", "updated_at", "pushed_at"]:
                    if field in doc and doc[field] is not None:
                        try:
                            if isinstance(doc[field], str):  # Convertir si c'est une chaîne
                                doc[field] = datetime.fromisoformat(doc[field].replace("Z", "+00:00"))
                        except ValueError:
                            print(f"⚠️ Erreur de format pour '{field}' dans le document '{doc['name']}', valeur ignorée.")
                            doc[field] = None  # Remplacer par None en cas d'erreur

                documents_to_insert.append(doc)

            # Insertion en base
            if documents_to_insert:
                result = self.collection.insert_many(documents_to_insert)
                inserted_ids = [str(_id) for _id in result.inserted_ids]
                return {"inserted_ids": inserted_ids, "message": "Insertion réussie ✅"}

            return {"message": "Aucun nouveau document à insérer."}

        except PyMongoError as e:
            print(f"❌ Erreur MongoDB lors de l'insertion : {e}")
            import traceback
            traceback.print_exc()
            return {"error": str(e)}

        
    def insert_ingestion_date(self, documents: List[dict]):
        """ Insère plusieurs documents dans MongoDB et recrée la collection si elle n'existe pas """
        if self.collection_data_ingestion is None or self.collection_data_ingestion_name not in self.db.list_collection_names():
            print(f"⚠️ Collection '{self.collection_data_ingestion_name}' absente. Création en cours...")
            self.collection_data_ingestion = self.db[self.collection_data_ingestion_name]  # Correction ici
            print(f"✅ Collection '{self.collection_data_ingestion_name}' créée avec succès.")

        try:
            existing_ids = {doc["id"] for doc in self.collection_data_ingestion.find({}, {"id": 1})}
            documents_to_insert = [doc for doc in documents if doc["id"] not in existing_ids]

            if documents_to_insert:
                result = self.collection_data_ingestion.insert_many(documents_to_insert)  # Correction ici
                inserted_ids = [str(_id) for _id in result.inserted_ids]  # Convertir ObjectId en string
                return {"inserted_ids": inserted_ids, "message": "Insertion réussie ✅"}

            return {"message": "Aucun nouveau document à insérer."}
        
        except Exception as e:
            print(f"❌ Erreur lors de l'insertion : {e}")
            import traceback
            traceback.print_exc()
            return {"error": str(e)}


    def display_documents(self, page: int = 1, page_size: int = 10):
        """ Retourne les documents paginés de la collection """
        if self.collection is None:
            return {"error": "Collection non initialisée"}
        
        # Calculer l'offset (skip)
        skip = (page - 1) * page_size

        try:
            cursor = self.collection.find({}, {"_id": 0}).skip(skip).limit(page_size)
            documents = list(cursor)
            
            # Compter le nombre total de documents pour la pagination
            total_documents = self.collection.count_documents({})
            total_pages = (total_documents + page_size - 1) // page_size  # Arrondi vers le haut

            return {
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "total_documents": total_documents,
                "data": documents
            }
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"error": str(e)}


    def display_ingestion_data(self):
        """ Retourne tous les documents de la collection """
        if self.collection_data_ingestion is None:
            return {"error": "collection_data_ingestion non initialisée"}

        try:
            cursor = self.collection_data_ingestion.find({}, {"_id": 0})
            data = list(cursor)  # Convertir proprement en liste
            return {"data": data, "message": "Données récupérées avec succès ✅"}
        except Exception as e:
            import traceback
            traceback.print_exc()  # Voir l'erreur complète dans les logs
            return {"error": str(e)}
        

    # Configuration du logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    def delete_collection(self, collection_name: str):
        """ Supprime une collection spécifique de la base de données """
        if self.db is None:
            logging.error("❌ Erreur : Base de données non connectée")
            return {"error": "Base de données non connectée"}
        
        try:
            # Récupérer la liste des collections avant suppression
            collections = self.db.list_collection_names()
            logging.info(f"📂 Collections existantes avant suppression : {collections}")

            if collection_name not in collections:
                logging.warning(f"⚠️ La collection '{collection_name}' n'existe pas, rien à supprimer.")
                return {"warning": f"La collection '{collection_name}' n'existe pas."}

            # Suppression de la collection
            logging.info(f"🗑 Suppression de la collection '{collection_name}'...")
            self.db.drop_collection(collection_name)
            
            # Vérification après suppression
            collections_after = self.db.list_collection_names()
            logging.info(f"📂 Collections restantes après suppression : {collections_after}")

            return {"message": f"Collection '{collection_name}' supprimée avec succès ✅"}
        
        except Exception as e:
            logging.error(f"❌ Erreur lors de la suppression de la collection '{collection_name}': {e}", exc_info=True)
            return {"error": str(e)}




    
    
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
    
    # Insertion des documents (repos GitHub)
    inserted_data = backForDatabase.insert_documents([doc.dict() for doc in documents])

    # Génération des objets DataIngestionDate avec la date par défaut
    ingestion_dates = [
        DataIngestionDate(id=doc.id, node_id=doc.node_id, ingestion_date=datetime.utcnow().isoformat())
        for doc in documents
    ]

    # Insertion des dates d'ingestion
    inserted_ingestion_date = backForDatabase.insert_ingestion_date([data.dict() for data in ingestion_dates])


    return {
        "message": "Données insérées",
        "data": inserted_data,
        "ingestion_data": inserted_ingestion_date
    }


@app.get("/show_data")
def show_data(page: int = 1, page_size: int = 10):
    """ Afficher les données avec pagination """
    return backForDatabase.display_documents(page, page_size)

@app.get("/count")
def count_documents():
    return backForDatabase.collection_data_ingestion.count_documents({})

@app.get("/get_ingestion_date")
def get_ingestion_date():
     return backForDatabase.display_ingestion_data()

@app.delete("/delete_collection/{collection_name}")
def delete_collection(collection_name: str):
    if backForDatabase.client is None:
        raise HTTPException(status_code=500, detail="Base de données non connectée")
    
    result = backForDatabase.delete_collection(collection_name)
    
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    
    return result
