import os

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.concurrency import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from mangum import Mangum

from app.prisma import prisma

from .api import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await prisma.prisma.connect()
    print("Connected to database")
    # consume_messages()
    # for group_id in ["soham1"]:
    # await start_consumer(group_id)
    # logger.info("Kafka consumers started")
    yield
    await prisma.prisma.disconnect()

app = FastAPI(lifespan=lifespan)

if os.path.exists(".env"):
    load_dotenv()

origin_prefix = "ORIGIN_"

origins = [
    "http://localhost",
    "https://localhost:3000",
    "http://localhost:8080",
]

TOTAL_ORIGINS = os.getenv("TOTAL_ORIGINS") or 0

for i in range(1, int(TOTAL_ORIGINS) + 1):
    origins.append(os.getenv(f"{origin_prefix}{i}"))

print(origins)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router=api_router.router)


@app.middleware("http")
async def global_exception_handler(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"message": f"An unexpected error occurred: {str(e)}"}
        )


@app.get('/')
def read_root():
    return {'Hello': 'World',
            'status': 'ok'}


handler = Mangum(app)
