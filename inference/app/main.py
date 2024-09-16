import uvicorn
from fastapi import FastAPI, Request
from fastapi.concurrency import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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
    return {'Hello': 'World'}

