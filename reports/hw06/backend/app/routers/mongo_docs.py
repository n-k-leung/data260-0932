# Route handlers (Part 1 - II: separate file for route handlers)
from datetime import datetime, timezone
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException
from pymongo.errors import PyMongoError

from ..mongo import get_collection
from ..mongo_schema import VulDocCreate, VulDocUpdate, VulDocOut

router = APIRouter(prefix="/api/vul-docs", tags=["Vulnerability Docs (MongoDB)"])

def now_utc():
    return datetime.now(timezone.utc)

def to_out(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    return doc

def parse_id(item_id: str) -> ObjectId:
    try:
        return ObjectId(item_id)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=400, detail="Invalid id format")

@router.post("", response_model=VulDocOut, status_code=201)
def create_doc(payload: VulDocCreate):
    col = get_collection()
    doc = payload.model_dump()
    doc["created_at"] = now_utc()
    doc["updated_at"] = doc["created_at"]
    try:
        result = col.insert_one(doc)
        return to_out(col.find_one({"_id": result.inserted_id}))
    except PyMongoError:
        raise HTTPException(status_code=500, detail="Database error while creating record")

@router.get("", response_model=list[VulDocOut])
def get_all_docs():
    try:
        return [to_out(d) for d in get_collection().find().sort("created_at", -1)]
    except PyMongoError:
        raise HTTPException(status_code=500, detail="Database error while fetching records")

@router.get("/{item_id}", response_model=VulDocOut)
def get_one_doc(item_id: str):
    oid = parse_id(item_id)
    try:
        doc = get_collection().find_one({"_id": oid})
    except PyMongoError:
        raise HTTPException(status_code=500, detail="Database error while fetching record")
    if not doc:
        raise HTTPException(status_code=404, detail="Record not found")
    return to_out(doc)

@router.put("/{item_id}", response_model=VulDocOut)
def update_doc(item_id: str, payload: VulDocUpdate):
    oid = parse_id(item_id)
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=400, detail="No fields provided to update")
    #updated at refreshes
    changes ["updated_at"] = now_utc()
    try:
        col = get_collection()
        result = col.update_one({"_id": oid}, {"$set": changes})
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Record not found")
        return to_out(col.find_one({"_id": oid}))
    except PyMongoError:
        raise HTTPException(status_code=500, detail="Database error while updating record")

@router.delete("/{item_id}")
def delete_doc(item_id: str):
    oid = parse_id(item_id)
    try:
        result = get_collection().delete_one({"_id": oid})
    except PyMongoError:
        raise HTTPException(status_code=500, detail="Database error while deleting record")
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Record not found")
    return {"message": "Deleted", "id": item_id}

