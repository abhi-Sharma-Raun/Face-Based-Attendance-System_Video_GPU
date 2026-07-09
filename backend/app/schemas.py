from pydantic import BaseModel
from typing import List
from datetime import date


class General_201_response(BaseModel):
    message: str

class PresentStudent(BaseModel):
    name: str
    roll_num: str
    
class Video_AttendanceResponse(BaseModel):
    students: List[PresentStudent]
    
class Face_registrationResponse(BaseModel):
    name: str
    roll_num: str
    
class TeacherCreate(BaseModel):
    name: str
    email: str
    department: str
    
class AdminCreate(BaseModel):
    name: str
    email: str

class ClassCreate(BaseModel):
    class_name: str
    batch_start_year: int
    curr_year: int
    course_id: str
    department: str
    branch: str
    
class AddSudents_class(BaseModel):
    student_roll_list: List[str]
    class_name: str
    
class Student_ViewAttendance_Response(BaseModel):
    roll_num: str
    present_dates: List[date]
    
class Teacher_ViewAttendance_Response(BaseModel):
    attendance_data: List[Student_ViewAttendance_Response]
    