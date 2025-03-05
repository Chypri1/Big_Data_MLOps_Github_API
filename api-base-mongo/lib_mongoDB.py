import threading
import json
from confluent_kafka import Consumer, KafkaError
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

MONGO_URI = os.getenv("MONGO_URI")
KAFKA_BROKER = os.getenv("KAFKA_BROKER")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC")

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
            self.client = MongoClient(self.connection_uri, serverSelectionTimeoutMS=5000)
            self.db = self.client[self.database_name]
            self.collection = self.db[self.collection_name]
            self.collection_data_ingestion = self.db[self.collection_data_ingestion_name]
            
            if self.collection is not None:
                print("Connexion réussie à MongoDB Cosmos DB")
            else:
                print("Erreur : Collection introuvable")
        except Exception as e:
            print(f"Erreur de connexion : {e}")
            self.client = None  

    from pymongo.errors import PyMongoError

    def insert_documents(self, documents: List[dict]):
        """ Insère plusieurs documents dans MongoDB et gère les erreurs de format de date """
        if self.collection is None or self.collection_name not in self.db.list_collection_names():
            print(f"Collection '{self.collection_name}' absente. Création en cours...")
            self.collection = self.db[self.collection_name]  # Creating collection
            print(f"Collection '{self.collection_name}' créée avec succès.")

        try:
            # Vérify to not have duplicate docs 
            existing_names = {doc["name"] for doc in self.collection.find({}, {"name": 1})}
            documents_to_insert = []

            for doc in documents:
                if doc["name"] in existing_names:
                    print(f"Le document '{doc['name']}' existe déjà, il ne sera pas inséré.")
                    continue

                # Vérify et convert dates (created_at, updated_at, pushed_at)
                for field in ["created_at", "updated_at", "pushed_at"]:
                    if field in doc and doc[field] is not None:
                        try:
                            if isinstance(doc[field], str):  
                                doc[field] = datetime.fromisoformat(doc[field].replace("Z", "+00:00"))
                        except ValueError:
                            print(f"Erreur de format pour '{field}' dans le document '{doc['name']}', valeur ignorée.")
                            doc[field] = None  

                documents_to_insert.append(doc)

            # Database insertion
            if documents_to_insert:
                result = self.collection.insert_many(documents_to_insert)
                inserted_ids = [str(_id) for _id in result.inserted_ids]
                return {"inserted_ids": inserted_ids, "message": "Insertion réussie"}

            return {"message": "Aucun nouveau document à insérer."}

        except PyMongoError as e:
            print(f"Erreur MongoDB lors de l'insertion : {e}")
            import traceback
            traceback.print_exc()
            return {"error": str(e)}

        
    def insert_ingestion_date(self, documents: List[dict]):
        """ Insère plusieurs documents dans MongoDB et recrée la collection si elle n'existe pas """
        if self.collection_data_ingestion is None or self.collection_data_ingestion_name not in self.db.list_collection_names():
            print(f"Collection '{self.collection_data_ingestion_name}' absente. Création en cours...")
            self.collection_data_ingestion = self.db[self.collection_data_ingestion_name]  
            print(f"Collection '{self.collection_data_ingestion_name}' créée avec succès.")

        try:
            existing_ids = {doc["id"] for doc in self.collection_data_ingestion.find({}, {"id": 1})}
            documents_to_insert = [doc for doc in documents if doc["id"] not in existing_ids]

            if documents_to_insert:
                result = self.collection_data_ingestion.insert_many(documents_to_insert) 
                inserted_ids = [str(_id) for _id in result.inserted_ids]
                return {"inserted_ids": inserted_ids, "message": "Insertion réussie"}

            return {"message": "Aucun nouveau document à insérer."}
        
        except Exception as e:
            print(f"Erreur lors de l'insertion : {e}")
            import traceback
            traceback.print_exc()
            return {"error": str(e)}


    def display_documents(self, page: int = 1, page_size: int = 10, date_begin: datetime = None, date_end: datetime = None):
        """ Retourne les documents paginés de la collection entre deux dates """
        if self.collection is None:
            return {"error": "Collection non initialisée"}

        # Valeurs par défaut si les dates ne sont pas fournies
        if date_begin is None:
            date_begin = datetime.min
        if date_end is None:
            date_end = datetime.max

        # Calcul du décalage pour la pagination
        skip = (page - 1) * page_size

        try:
            # Filtrer par date et paginer les résultats
            cursor = self.collection.find(
                {"created_at": {"$gte": date_begin, "$lte": date_end}},
                {"_id": 0}
            ).skip(skip).limit(page_size)

            documents = list(cursor)

            # Compter le nombre total de documents correspondant au filtre
            total_documents = self.collection.count_documents({"created_at": {"$gte": date_begin, "$lte": date_end}})
            total_pages = (total_documents + page_size - 1) // page_size

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
            data = list(cursor)  # convert to list
            return {"data": data, "message": "Données récupérées avec succès"}
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"error": str(e)}
        

    # logging Configuration 
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    def delete_collection(self, collection_name: str):
        """ Supprime une collection spécifique de la base de données """
        if self.db is None:
            logging.error("Erreur : Base de données non connectée")
            return {"error": "Base de données non connectée"}
        
        try:
            
            collections = self.db.list_collection_names()
            logging.info(f"Collections existantes avant suppression : {collections}")

            if collection_name not in collections:
                logging.warning(f"La collection '{collection_name}' n'existe pas, rien à supprimer.")
                return {"warning": f"La collection '{collection_name}' n'existe pas."}

            logging.info(f"Suppression de la collection '{collection_name}'...")
            self.db.drop_collection(collection_name)
            
            collections_after = self.db.list_collection_names()
            logging.info(f"Collections restantes après suppression : {collections_after}")

            return {"message": f"Collection '{collection_name}' supprimée avec succès"}
        
        except Exception as e:
            logging.error(f"Erreur lors de la suppression de la collection '{collection_name}': {e}", exc_info=True)
            return {"error": str(e)}




    
    
# Initialisation avec l'URI Cosmos DB
backForDatabase = BackForDatabase(connection_uri=MONGO_URI)
backForDatabase.connect_to_mongo()

# fastapi and endpoint creations, instanciations
app = FastAPI()

@app.get("/")
def base():
    return {"message": "Client connecté !" if backForDatabase.client else "Client non connecté !"}

@app.get("/hello_world")
def hello_world():
    return {"message": "Hello, world!"}

@app.post("/add_data")
def add_data(documents: List[DocumentModel]):
    return adding_data_from_endpoint(documents)

@app.get("/show_data")
def show_data(page: int = 1, page_size: int = 10,date = datetime.now()):
    """ Afficher les données avec pagination """
    return backForDatabase.display_documents(page, page_size,date)

@app.get("/count")
def count_documents():
    return backForDatabase.collection.count_documents({})

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


# function to add data from endpoint or kafka 
def adding_data_from_endpoint(documents):
    if backForDatabase.client is None:
        raise HTTPException(status_code=500, detail="Base de données non connectée")
    
    inserted_data = backForDatabase.insert_documents([doc.dict() for doc in documents])

    ingestion_dates = [
        DataIngestionDate(id=doc.id, node_id=doc.node_id, ingestion_date=datetime.utcnow().isoformat())
        for doc in documents
    ]

    # Insertion ingestion date
    inserted_ingestion_date = backForDatabase.insert_ingestion_date([data.dict() for data in ingestion_dates])


    return {
        "message": "Données insérées",
        "data": inserted_data,
        "ingestion_data": inserted_ingestion_date
    }

def adding_data_from_kafka(msg):
    try:
        data = json.loads(msg.value().decode('utf-8'))
        print("Message reçu :", data)

        # Insert in MongoDB
        if not (backForDatabase.client is None):
                backForDatabase.insert_documents([data])
                ingestion_data = DataIngestionDate(id=data["id"], node_id=data["node_id"]).dict()
                backForDatabase.insert_ingestion_date([ingestion_data])
                return {"message":"BASE INSERER"}
        else:
            return {"message":"ERREUR INSERTION BASE"}

    except json.JSONDecodeError:
        print("Message reçu (non-JSON):", msg.value().decode('utf-8'))


# Kafka consumer configuration 
conf = {
    'bootstrap.servers': KAFKA_BROKER,
    'group.id': 'mon-groupe-consumer',
    'auto.offset.reset': 'earliest', # param for reading from the beggining
}

consumer = Consumer(conf)
consumer.subscribe([KAFKA_TOPIC])

# Kafka Consumer in background
def kafka_consumer():
    """ Fonction pour consommer les messages Kafka et les insérer dans MongoDB """
    try:
        while True:
            messages = consumer.consume( timeout=5.0)
            if not messages:
                continue  # passive waiting

            for msg in messages:
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        print(f"Fin de partition {msg.topic()} [{msg.partition()}]")
                    else:
                        print(f"Erreur: {msg.error()}")
                else:
                    return adding_data_from_kafka(msg)

    except KeyboardInterrupt:
        print("Arrêt du consumer Kafka")
    finally:
        consumer.close()

# Démarrer le consumer Kafka dans un thread
kafka_thread = threading.Thread(target=kafka_consumer, daemon=True)
kafka_thread.start()

print("Consumer Kafka lancé en arrière-plan")

