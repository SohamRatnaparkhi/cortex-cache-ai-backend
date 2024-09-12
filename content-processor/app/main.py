import asyncio
import json
import logging
from contextlib import asynccontextmanager

from aiokafka import AIOKafkaConsumer
from app.utils.Kafka import kafka_consumer_task
from fastapi import BackgroundTasks, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from kafka import KafkaConsumer

from .api import router
from .prisma import prisma

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await prisma.prisma.connect()
    # consume_messages()
    # for group_id in ["soham1"]:
        # await start_consumer(group_id)
    # logger.info("Kafka consumers started")
    yield
    await prisma.prisma.disconnect()

app = FastAPI(lifespan=lifespan)

origins = [
    "http://localhost",
    "https://localhost:3000",
    "http://localhost:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router=router.router)

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.middleware("http")
async def global_exception_handler(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"message": f"An unexpected error occurred: {str(e)}"}
        )

@app.get("/kafka-init/{group_id}",
         tags=["Kafka"])
async def kafka_init(group_id: str):
    try:
        await start_consumer(group_id)
        return {"message": "Kafka consumer initialized"}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"message": f"Failed to initialize Kafka consumer: {str(e)}"}
        )


async def start_consumer(group_id: str):
    task = asyncio.create_task(kafka_consumer_task(group_id))
    logger.info(f"Kafka consumer {group_id} started")
    # consumer_tasks[group_id] = task
    return task
