from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.kafka_rpc import KafkaRPC

rpc = KafkaRPC()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await rpc.start()
    print("FastAPI server started at http://127.0.0.1:8032")
    yield
    await rpc.stop()


app = FastAPI(title="Vulnerability Kafka Demo", lifespan=lifespan)


@app.get("/")
async def home():
    return {"message": "FastAPI service running"}


# Kafka-based endpoint
@app.post("/vuls")
async def handle_vulnerability_operation(payload: dict):
    response = await rpc.make_request(payload)
    return response