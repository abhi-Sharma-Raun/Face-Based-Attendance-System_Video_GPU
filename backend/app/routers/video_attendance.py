import tempfile
import shutil
import time
import cv2
import numpy as np
import traceback
from fastapi import APIRouter, UploadFile, File, HTTPException, status, Form, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select, insert
from datetime import date
from ..utils.models_frame_selection import select_nbd_frame_batch, get_det_rec_model
from ..utils.qdrant_utils import qdrant_cosine_search
from .. import schemas, models
from ..config import settings
from ..database import get_db

router = APIRouter(
    prefix="/video_attendance",
    tags=["video_attendance"]
)

FACE_SIMILARITY_THRESHOLD = 0.55

@router.post("", response_model=schemas.Video_AttendanceResponse)
async def mark_attendance(class_name: str = Form(...), video: UploadFile = File(...), db: Session = Depends(get_db)):
    
    det_rec_model = get_det_rec_model()
    
    if not det_rec_model:
        print("Face detection and recognition models are not initialized.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Face detection and recognition models are not initialized.")
    s_time = time.time()
    
    t_class = db.scalars(select(models.Class).where(models.Class.class_name == class_name)).one_or_none()
    if t_class is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="The class does not exists")
    enrolled_students = t_class.enrolled_students
    if not enrolled_students:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="There are no enrolled students in the class")
    
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
            best_frame, tot_face_detected = select_nbd_frame_batch(frame_num, vid, tot_frames)
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
        enrolled_studs_rolls = [stud.roll_num for stud in enrolled_students]
        qd_response = qdrant_cosine_search(extracted_embeddings, purpose="attendance", studs_ids=enrolled_studs_rolls)
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
    
    if len(pres_studs_roll)==0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="There are no students of the class in the image")
    
    present_students_db = [ {"class_id":t_class.class_id, "student_roll":roll, "attendance_date":date.today()} for roll in pres_studs_roll]
    stmt = insert(models.Attendance).on_conflict_do_nothing(index_elements=["student_roll", "attendance_date", "class_id"])
    db.execute(stmt, present_students_db)
    
    db.commit()
    print(f"TOTAL EXECUTION PIPELINE LATENCY: {time.time() - s_time:.4f} seconds")
    return schemas.Video_AttendanceResponse(students=pres_studs_details)