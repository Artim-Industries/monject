from pymongo import *
import yaml
from fastapi import HTTPException
from bson import ObjectId

class Connection:
    def __init__(self, queryString = None):
        with open("config.yml", "r") as configFile:
            config = yaml.safe_load(configFile)

        self.username = config[0]["Database"][2]["username"]
        self.password = config[0]["Database"][4]["password"]
        self.host = config[0]["Database"][0]["host"]
        self.port = config[0]["Database"][1]["port"]
        self.database = config[0]["Database"][3]["database"]

        self.queryString = queryString if queryString else f"mongodb://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}?authSource=admin"
        self.client = MongoClient(self.queryString)

    def __del__(self):
        self.client.close()

    @property
    def db(self):
        return self.client[self.database]

    def getCollection(self, collection, items: int = 30, page: int = 0):
        documents = []
        for doc in self.db[collection].find():
            doc["_id"] = str(doc["_id"])
            documents.append(doc)

        documents = {
            "data": documents[items * page: items * (page + 1)] if items > 0 else documents,
            "pagination": {
                "total": len(documents),
                "items": items,
                "page": page,
                "pages": len(documents) // items if items > 0 else 1
            },
            "note": "This is a paginated response. Use the page parameter to navigate through the response or disable pagination by settings items = 0."
        } if len(documents) > items else {
            "data": documents,
            "pagination": {
                "total": len(documents),
                "items": items,
                "page": page,
                "pages": len(documents) // items if items > 0 else 1
            },
        }

        return documents

    def getDocuments(self, collection, query, items: int = 30, page: int = 0):
        documents = []
        for doc in self.db[collection].find(query):
            doc["_id"] = str(doc["_id"])
            documents.append(doc)
            
        documents = {
            "data": [doc for doc in documents[items * page: items * (page + 1)]] if items > 0 else documents,
            "pagination": {
                "total": len(documents),
                "items": items,
                "page": page,
                "pages": len(documents) // items if items > 0 else 1
            },
            "note": "This is a paginated response. Use the page parameter to navigate through the response or disable pagination by settings items = 0."
        } if len(documents) > items else {
            "data": documents,
            "pagination": {
                "total": len(documents),
                "items": items,
                "page": page,
                "pages": len(documents) // items if items > 0 else 1
            },
        }
    
        return documents

    def getDocument(self, collection, query):
        doc = self.db[collection].find_one(query)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        doc["_id"] = str(doc["_id"])

        return doc

    def saveDocument(self, collection, document):
        print(document["_id"])
        return self.db[collection].insert_one(document)

    def updateDocument(self, collection, query, document):
        if document["_id"]:
            del document["_id"]
            
        document = {"$set": document}
    
        return self.db[collection].update_one(query, document)

    def deleteDocument(self, collection, query):
        return self.db[collection].delete_one(query)