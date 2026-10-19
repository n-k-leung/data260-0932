import os
from typing import get_args
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from .mongo_schema import StatusType, CategoryType

load_dotenv()

SID4 = "0932"
PREFIX = "s" + SID4

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB = os.getenv("MONGODB_DB", PREFIX + "_doc")
COLLECTION_NAME = "vulnerability_docs"

MESSAGES_COLLECTION = "messages"
SUMMARIES_COLLECTION = "summaries"
EPISODES_COLLECTION = "episodes"
client = MongoClient(MONGODB_URI)

def get_db():
    return client[MONGODB_DB]

def get_collection():
    return get_db()[COLLECTION_NAME]

def setup_collection():
    try:
        db = get_db()
        if COLLECTION_NAME in db.list_collection_names():
            return
        db.create_collection(
            COLLECTION_NAME,
            validator={
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": ["title", "status", "category", "discovered_at", "created_at", "updated_at"],
                    "properties": {
                        #string length limit
                        "title": {"bsonType": "string", "minLength": 1, "maxLength": 100},
                        "description": {"bsonType": ["string", "null"]},
                        #enum constraints
                        "status": {"enum": list(get_args(StatusType))},
                        "category": {"enum": list(get_args(CategoryType))},
                        "discovered_at": {"bsonType": "date"},
                        "created_at": {"bsonType": "date"},
                        "updated_at": {"bsonType": "date"},
                    },
                }
            },
        )
        print("Created collection", COLLECTION_NAME)
    except PyMongoError as e:
        print("MongoDB setup warning:", e)