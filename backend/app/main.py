from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import face_registration, video_attendance
from .config import settings

app = FastAPI()

app.include_router(face_registration.router)
app.include_router(video_attendance.router)


app.add_middleware(
    CORSMiddleware,
    allow_origins = [settings.allowed_url_1, settings.allowed_url_2, settings.allowed_url_3],
    allow_credentials = True,
    allow_methods = ["*"],
    allow_headers = ["*"]
)

@app.get("/")
def read_root(): 
    return {"message": "Welcome to our application"}