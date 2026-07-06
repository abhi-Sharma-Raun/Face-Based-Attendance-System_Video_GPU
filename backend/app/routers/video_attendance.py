import tempfile
import shutil
import time
import cv2
import numpy as np
import traceback
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from qdrant_client.models import QueryRequest, SearchParams
from .. import utils, schemas
from ..qdrant_setup import client, collection_name
from ..config import settings

router = APIRouter(
    prefix="/video_attendance",
    tags=["video_attendance"]
)

FACE_SIMILARITY_THRESHOLD = 0.55

@router.post("", response_model=schemas.Video_AttendanceResponse)
async def mark_attendance(video: UploadFile = File(...)):
    
    det_rec_model = utils.get_det_rec_model()
    det_model = utils.get_det_model()
    if not det_rec_model or not det_model:
        print("Face detection and recognition models are not initialized.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Face detection and recognition models are not initialized.")
    s_time = time.time()
    
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
            shutil.copyfileobj(video.file, tmp)
            video_path = tmp.name
    except Exception:
        print("Problem processing incoming video file stream")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Problem processing incoming video file stream")
    
    vid = cv2.VideoCapture(video_path)
    tot_frames = int(vid.get(cv2.CAP_PROP_FRAME_COUNT))
    k_fps = int(vid.get(cv2.CAP_PROP_FPS)) if vid.get(cv2.CAP_PROP_FPS) > 0 else 30
    
    N = int(settings.tot_secs_nbd * k_fps / settings.num_frame_select)
    if N < 1: 
        N = 1
        
    best_frames = []
    tot_best_faces = 0
    target_frames = list(range(N, tot_frames + 1, N))
    
    print(f"Total target frames: {len(target_frames)}")
    
    try:
        # Utilize optimized neighborhood batch evaluator
        for frame_num in target_frames:
            best_frame, tot_face_detected = utils.select_nbd_frame_batch(frame_num, vid, tot_frames)
            tot_best_faces += tot_face_detected
            if tot_face_detected!=0:
                best_frames.append(best_frame)
    except Exception as e:
        print(f"Frame selection execution failure: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to process video frames safely.")
    finally:
        vid.release()

    if not best_frames:
        print("Sent video has no readable frame streams.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sent video has no readable frame streams.")
    
    print(f"! Frame Selection Done ! total best frames: {len(best_frames)}")
    
    # Extract facial embeddings
    extracted_embeddings = []
    for frame in best_frames:
        try:
            faces = det_rec_model.get(frame)
        except Exception as e:
            print(f"InsightFace recognition failure: {e}")
            traceback.print_exc()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to extract recognition embeddings")
        
        for face in faces:
            emb = face.embedding
            norm = np.linalg.norm(emb)
            normalized_emb = emb / norm if norm > 0 else emb
            extracted_embeddings.append(normalized_emb)
            
    if not extracted_embeddings:
        print("No faces matching baseline standards found in sample arrays.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No faces matching baseline standards found in sample arrays.")
        
    print(f"! Embedding Extraction done for recognition !")
    
    try:
        CHUNK_SIZE=45
        params = SearchParams(exact=True)
        search_queries = [QueryRequest(query=v.tolist(), limit=1, score_threshold=FACE_SIMILARITY_THRESHOLD, with_payload=True, with_vector=False, params=params) for v in extracted_embeddings]
        qd_response = []
        for i in range(0, len(search_queries), CHUNK_SIZE):
            batch = search_queries[i:i + CHUNK_SIZE]
            batch_response = client.query_batch_points(
                collection_name = collection_name,
                requests = batch
            )
            qd_response.extend(batch_response)
    except Exception:
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Vector DB similarity search failed")
    
    pres_studs_roll = []
    pres_studs_details = []
    print(qd_response)
    for result in qd_response:
        
        if result.points and (result.points[0].payload["roll_num"] not in pres_studs_roll):
            roll_num = result.points[0].payload["roll_num"]
            name = result.points[0].payload["name"]
            pres_studs_roll.append(roll_num)
            pres_studs_details.append(schemas.PresentStudent(roll_num = roll_num, name=name))
            
    print(f"TOTAL EXECUTION PIPELINE LATENCY: {time.time() - s_time:.4f} seconds")
    return schemas.Video_AttendanceResponse(students=pres_studs_details)