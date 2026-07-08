from fastapi import router, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select
import uuid_utils
from qdrant_client.models import Distance, VectorParams, HnswConfigDiff
from typing import List
from .. import schemas, models
from ..database import get_db
from ..qdrant_setup import client


router = router.APIRouter(
    tags=["Teachers and Classes"],
)

@router.post("/teachers/add_teacher", response_model=schemas.General_201_response)
def add_teacher(teacher: schemas.TeacherCreate, db: Session = Depends(get_db)):
    
    if db.query(models.Teacher).filter(models.Teacher.email == teacher.email).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Teacher with email {teacher.email} already exists")
    
    user_id=uuid_utils.uuid7()
    
    new_user = models.Users(user_id=user_id, role="teacher", email=teacher.email)    
    new_teacher = models.Teacher(user_id=user_id, name=teacher.name, email=teacher.email, department=teacher.department)
    db.add(new_user)
    db.add(new_teacher)
    db.commit()
    
    response = schemas.General_201_response(message=f"Teacher {teacher.name} added successfully in department {teacher.department}")
    return response

@router.post("/teacher/remove_teacher")
def remove_teacher(teacher, db:Session = Depends(get_db)):
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented now")

    
@router.post("/class/add_class", response_model=schemas.General_201_response)
def add_class(class_d: schemas.ClassCreate, db: Session = Depends(get_db)):
    
    filter1 = (models.Class.batch_start_year == class_d.batch_start_year) and (models.Class.curr_year == class_d.curr_year) and (models.Class.branch == class_d.branch)
    dupl =  db.query(models.Class).filter((models.Class.class_name == class_d.class_name) or filter1).first()  
      
    if dupl and dupl.class_name == class_d.class_name:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"The class {class_d.class_name} exists")
    elif dupl:
        raise HTTPException(staus_code=status.HTTP_409_CONFLICT, detail=f"There is already class-{dupl.class_name} for batch-{dupl.batch_start_year} current year-{dupl.curr_year} for branch-{dupl.branch} and course-{dupl.course_id}")
    else:
        pass
    
    class_id = uuid_utils.uuid7()
    new_class = models.Class(class_id=class_id, class_name=class_d.class_name, batch_start_year=class_d.batch_start_year,
                             curr_year=class_d.curr_year, course_id=class_d.course_id, department=class_d.department, branch=class_d.branch)

    db.add(new_class)
    db.commit()
    
    response = schemas.General_201_response(message=f"Class-{class_d.class_name} for course-{class_d.course_id}, branch-{class_d.branch} and batch-{class_d.branch} registered successfully")    
    return response


@router.post("/class/add_students")
def add_student_class(students_class_data: schemas.AddSudents_class, db: Session=Depends(get_db)):
    
    students_roll_list = students_class_data.student_roll_list
    class_name = students_class_data.class_name
     
    stud_not_exists = None
    stmt = select(models.Students).where(models.Students.roll_num.in_(students_roll_list))
    students = db.scalars(stmt).all()
    exist_studs_rolls = [stud.roll_num for stud in students]
    if len(students) != len(students_roll_list):
        stud_not_exists = [stud_roll for stud_roll in students_roll_list if stud_roll not in exist_studs_rolls]
    
    t_class =  db.scalars(select(models.Class).where(models.Class.class_name == class_name)).one_or_none
    if not t_class:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="There is no class with this name")
    
    t_class.enrolled_students.extend(students)
    
    db.commit()
    
    response_str = "All students are registered"
    if len(stud_not_exists)>0:
        response_str+f" except following--- {stud_not_exists}"
    
    return schemas.General_201_response(message=response_str)
    
        
    