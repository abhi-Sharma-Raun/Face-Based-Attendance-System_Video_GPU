from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from typing import List
import random
import time
from qdrant_client.models import PointStruct
from .. import utils, schemas
from ..qdrant_setup import client, collection_name


router = APIRouter(
    prefix="/student_registration",
    tags=["Student Registration"]
)


@router.post("", response_model = schemas.Face_registrationResponse)
async def register_profile(name: str = Form(...), email: str = Form(...),
    files: List[UploadFile] = File(...)
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
        front_emb, left_emb, right_emb = map(utils.get_face_register_embedding, (front_profile, left_profile, right_profile))
                                                                           #Write a check to ensure that the profile belong to the same person
    except Exception as e:
        print(e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="No Problem from your side.This is our")
        

    if front_emb is None or left_emb is None or right_emb is None:
        raise HTTPException(status_code=400, detail = "No Face or Multiple Faces Detected in one of the profiles. Please ensure each profile contains exactly one face.")
    
    roll_num = random.randint(1000, 999999)*5
    try:
        payload = {"course": "B.Tech","name": name, "email": email, "roll_num": roll_num}
        points=[]
        points.append(PointStruct(id =roll_num+0, vector=front_emb, payload=payload))
        points.append(PointStruct(id =roll_num+1, vector=left_emb, payload=payload))
        points.append(PointStruct(id =roll_num+2, vector=right_emb, payload=payload))
        client.upsert(
            collection_name=collection_name,
            points = points
        )
    except Exception as e:
        print(e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="No Problem from your side.This is our")
    
    print(f"{roll_num} registered successfully")
    
    response = schemas.Face_registrationResponse(name= name, roll_num= roll_num)
    print(f"TOTAL TIME: {time.time() - s_time}")
    return response
