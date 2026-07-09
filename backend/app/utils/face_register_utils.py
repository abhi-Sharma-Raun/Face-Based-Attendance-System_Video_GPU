import cv2
import numpy as np
from .models_frame_selection import get_det_rec_model 

def get_face_register_embedding(ud_raw_prof_bytes):
    det_rec_model = get_det_rec_model()
    try:
        ud_profile = np.frombuffer(ud_raw_prof_bytes, dtype=np.uint8)
        profile = cv2.imdecode(ud_profile, cv2.IMREAD_COLOR)
    except Exception:
        raise Exception("Unable to decode image bytes")
        
    faces = det_rec_model.get(profile)
    if len(faces) != 1:
        return None
        
    embedding = faces[0].embedding
    norm = np.linalg.norm(embedding)
    return embedding / norm if norm > 0 else embedding

def is_3profiles_same_person(front_emb: np.ndarray, left_emb: np.ndarray, right_emb: np.ndarray) -> bool:
    
    emb_matrix = np.stack((front_emb, left_emb, right_emb))
    cosine_sim = np.matmul(emb_matrix, emb_matrix.T)
    front_left, front_left, front_right = cosine_sim[0][1], cosine_sim[0][2], cosine_sim[1][2]
    if front_left>0.5 and front_right>0.5 and front_left>0.5:
        return True
    else:
        return False
    