from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import Optional, List
from datetime import date
import csv
import io
from .. import schemas, models
from ..database import get_db


router = APIRouter(
    prefix="/attendance",
    tags=["Student Registration"]
)

@router.get("/view-attendance/by_student/{roll_num}/{class_name}", response_model=schemas.Student_ViewAttendance_Response)
def view_attendance_student(roll_num: str, class_name: str, db: Session=Depends(get_db),
                    start_date: Optional[date] = Query(None, description="Filter from this date (YYYY-MM-DD)"),
                    end_date: Optional[date] = Query(None, description="Filter from this date (YYYY-MM-DD)")):
    '''
    This route is for students for viewing their attendance
    '''
    
    
    t_class = db.scalars(select(models.Class).where(models.Class.class_name==class_name)).one_or_none()
    if not t_class:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="The class do not exists")
    
    stmt = select(models.Attendance).where(models.Attendance.class_id==t_class.class_id, models.Attendance.student_roll==roll_num)
    if start_date:
        stmt = stmt.where(models.Attendance.attendance_date >= start_date)
    if end_date:
        stmt = stmt.where(models.Attendance.attendance_date <= end_date)
    stmt = stmt.order_by(models.Attendance.attendance_date.asc())
    attendance = db.scalars(stmt).all()
    
    attendance_record_list = [record.attendance_date.isoformat() for record in attendance]
    
    return {"present_dates": attendance_record_list, "roll_num": roll_num}


@router.post("/view-attendance/by_teacher")
def view_attendance_teacher(class_name: str, students_roll_list: List[str]=None, db: Session=Depends(get_db)):
    '''
    This route is for teacher for viewing the attendance of selective students. If no students are provided, all students attendance is returned.
    '''
    
    t_class = db.scalars(select(models.Class).where(models.Class.class_name==class_name)).one_or_none()
    if not t_class:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="The class do not exists")
    
    stmt = select(models.Attendance).where(models.Attendance.class_id==t_class.class_id)
    if students_roll_list is not None:
        stmt = stmt.where(models.Attendance.student_roll.in_(students_roll_list))
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Roll_no", "Present_dates"])
        
    attendance_record = db.scalars(stmt).all()
    res={}
    for v in attendance_record:
        roll_num=v.student_roll
        res.get(roll_num, []).append(v.attendance_date.isoformat())
        
    for roll_num, pres_dates in res.items():
        writer.writerow([roll_num, ", ".join(pres_dates)])
        
    output.seek(0)
    
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"content-disposition": "attachement; filename=attendance.csv"}
    )
        
        
    
    