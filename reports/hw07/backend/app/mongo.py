import os
from typing import get_args

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from .mongo_schema import CategoryType, StatusType

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
                    "required": [
                        "title",
                        "status",
                        "category",
                        "discovered_at",
                        "created_at",
                        "updated_at",
                    ],
                    "properties": {
                        # string length limit
                        "title": {
                            "bsonType": "string",
                            "minLength": 1,
                            "maxLength": 100,
                        },
                        "description": {"bsonType": ["string", "null"]},
                        # enum constraints
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


def get_messages_col():
    return get_db()[MESSAGES_COLLECTION]


def get_summaries_col():
    return get_db()[SUMMARIES_COLLECTION]


def get_episodes_col():
    return get_db()[EPISODES_COLLECTION]


def setup_memory_collections():
    try:
        db = get_db()
        existing = db.list_collection_names()

        if MESSAGES_COLLECTION not in existing:
            db.create_collection(
                MESSAGES_COLLECTION,
                validator={
                    "$jsonSchema": {
                        "bsonType": "object",
                        "required": [
                            "user_id",
                            "session_id",
                            "role",
                            "content",
                            "created_at",
                        ],
                        "properties": {
                            "user_id": {"bsonType": "string"},
                            "session_id": {"bsonType": "string"},
                            "role": {"enum": ["user", "assistant"]},
                            "content": {"bsonType": "string"},
                            "created_at": {"bsonType": "date"},
                        },
                    }
                },
            )
        if SUMMARIES_COLLECTION not in existing:
            db.create_collection(
                SUMMARIES_COLLECTION,
                validator={
                    "$jsonSchema": {
                        "bsonType": "object",
                        "required": [
                            "user_id",
                            "session_id",
                            "scope",
                            "text",
                            "created_at",
                        ],
                        "properties": {
                            "user_id": {"bsonType": "string"},
                            "session_id": {"bsonType": ["string", "null"]},
                            "scope": {"enum": ["session", "user"]},
                            "text": {"bsonType": "string"},
                            "created_at": {"bsonType": "date"},
                        },
                    }
                },
            )
        if EPISODES_COLLECTION not in existing:
            db.create_collection(
                EPISODES_COLLECTION,
                validator={
                    "$jsonSchema": {
                        "bsonType": "object",
                        "required": [
                            "user_id",
                            "session_id",
                            "fact",
                            "importance",
                            "embedding",
                            "created_at",
                        ],
                        "properties": {
                            "user_id": {"bsonType": "string"},
                            "session_id": {"bsonType": "string"},
                            "fact": {"bsonType": "string", "maxLength": 200},
                            "importance": {
                                "bsonType": ["double", "int"],
                                "minimum": 0,
                                "maximum": 1,
                            },
                            "embedding": {"bsonType": "array"},
                            "created_at": {"bsonType": "date"},
                        },
                    }
                },
            )

        get_messages_col().create_index(
            [("user_id", 1), ("session_id", 1), ("created_at", 1)]
        )
        get_summaries_col().create_index([("user_id", 1), ("created_at", 1)])
        get_episodes_col().create_index([("user_id", 1), ("created_at", 1)])
    except PyMongoError as e:
        print("MongoDB memory setup warning:", e)
