from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    num_eval_nbd_frames: int
    sharpness_threshold: int
    face_size_threshold: int
    pose_symmetry_threshold: float
    qdrant_url: str
    qdrant_api_key: str
    class Config:
        env_file = ".env"
    
settings = Settings()
    