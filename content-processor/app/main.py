from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from .api import router
from .prisma import prisma

app = FastAPI()
app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.on_event("startup")
async def startup():
    await prisma.prisma.connect()


@app.on_event("shutdown")
async def shutdown():
    await prisma.prisma.disconnect()
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
