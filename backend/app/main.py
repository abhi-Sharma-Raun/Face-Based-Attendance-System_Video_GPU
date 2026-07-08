import anyio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from .utils import models_frame_selection
from .routers import face_registration, video_attendance, view_attendance, teachers_class
from .config import settings
from . import models, database


@asynccontextmanager
async def lifespan(app: FastAPI):
    await anyio.to_thread.run_sync(models_frame_selection.get_det_model)
    await anyio.to_thread.run_sync(models_frame_selection.get_det_rec_model)
    print("Models loaded successfully")
    await anyio.to_thread.run_sync(models.Base.metadata.create_all, database.engine)
    
    yield
    
    print("Application shutdown")



app = FastAPI(lifespan=lifespan)

app.include_router(face_registration.router)
app.include_router(video_attendance.router)
app.include_router(view_attendance.router)
app.include_router(teachers_class.router)

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