from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    num_eval_nbd_frames: int
    sharpness_threshold: int
    face_size_threshold: int
    pose_symmetry_threshold: float
    face_similarity_threshold: float
    tot_secs_nbd: int
    num_frame_select: int
    qdrant_url: str
    qdrant_api_key: str
    allowed_url_1: str
    allowed_url_2: str
    allowed_url_3: str
    class Config:
        env_file = ".env"
    
settings = Settings()
    