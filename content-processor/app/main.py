from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routers import audio, files, image, link, video

app = FastAPI()

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

app.include_router(video.router)
app.include_router(audio.router)
app.include_router(image.router)
app.include_router(link.router)
app.include_router(files.router)

@app.get("/")
async def root():
    return {"message": "Hello World"}