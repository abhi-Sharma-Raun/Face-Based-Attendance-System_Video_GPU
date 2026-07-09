from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status, Depends
from sqlalchemy.orm import Session
from typing import List
import time
from qdrant_client.models import PointStruct
import uuid_utils.compat as uuid_utils
import traceback
from ..utils.face_register_utils import get_face_register_embedding, is_3profiles_same_person
from .. import schemas, models
from ..database import get_db
from ..qdrant_setup import client
from ..config import settings
from ..utils.qdrant_utils import qdrant_cosine_search


router = APIRouter(
    prefix="/student_registration",
    tags=["Student Registration"]
)


@router.post("", response_model = schemas.Face_registrationResponse)
async def register_profile(name: str = Form(...), email: str = Form(...), roll_num:str = Form(...),
    files: List[UploadFile] = File(...), db:Session=Depends(get_db)
    ):
    
    s_time = time.time()
    front_profile = None
    left_profile = None
    right_profile = None
    
    try:
        for file in files:
            raw_profile = await file.read()
            if file.filename == "front.jpg":
                front_profile = raw_profile
            elif file.filename == "left.jpg":
                left_profile = raw_profile
            elif file.filename == "right.jpg":
                right_profile = raw_profile
    except Exception as e:
        print(e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unable to read the images")
            
    if not front_profile or not left_profile or not right_profile:
        raise HTTPException(status_code=400, detail="All three profiles (front.jpg, left.jpg, right.jpg) are required.")
    
    try:
        front_emb, left_emb, right_emb = map(get_face_register_embedding, (front_profile, left_profile, right_profile))                                                                   
    except Exception as e:
        print(e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="No Problem from your side.This is our")  
    if front_emb is None or left_emb is None or right_emb is None:
        raise HTTPException(status_code=400, detail = "No Face or Multiple Faces Detected in one of the profiles. Please ensure each profile contains exactly one face.")
    if not is_3profiles_same_person(front_emb, left_emb, right_emb):
        print("ALL profiles must be of same person")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="All the 3 profiles must belong to same person")
    
    
    #check to ensure there are no 2 students with same image
    q_resp = qdrant_cosine_search([front_emb, left_emb, right_emb], purpose="Face_registration")
    print(q_resp)
    is_person_exists_qdrant=False
    exist_person_roll=set()
    for v in q_resp:
        if v.points:
            exist_person_roll.add(v.points[0].payload["roll_num"])
            is_person_exists_qdrant=True
            break  
    if is_person_exists_qdrant:  #Try to add the roll_num of the student with whom is the conflict
        print("There is already a person with same image")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"There is already a person with roll_num--{exist_person_roll} with same image.")
    
    user_id = uuid_utils.uuid7()
    new_user = models.Users(user_id=user_id, role="student", email= email)
    new_student = models.Students(user_id=user_id, name=name, roll_num=roll_num, email=email)
    db.add(new_user)
    db.flush()
    db.add(new_student)
    
    try:
        payload_ = {"course": "B.Tech", "name": name, "roll_num": roll_num, "user_id":user_id}
        vectors = {
            "front": front_emb,
            "left": left_emb,
            "right": right_emb,
        }
        client.upsert(
            collection_name="Face_Embeddings-All",   
            points = [PointStruct(id=user_id, vector=vectors, payload=payload_)]
        )
    except Exception as e:
        traceback.print_exc()
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="No Problem from your side.This is our")
    
    db.commit()
    
    print(f"{roll_num} registered successfully")
    response = schemas.Face_registrationResponse(name= name, roll_num= roll_num)
    print(f"TOTAL TIME: {time.time() - s_time}")
    return response
