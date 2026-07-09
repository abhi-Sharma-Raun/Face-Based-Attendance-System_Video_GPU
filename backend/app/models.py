from datetime import datetime, date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Column,String, ForeignKey, UniqueConstraint, Enum, Table, Date
from sqlalchemy.sql.sqltypes import TIMESTAMP, INTEGER
from sqlalchemy.sql.expression import text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import uuid_utils
from typing import Literal, List
from .database import Base


user_roles = Literal["teacher", "admin", "student"]
class Users(Base):
    __tablename__="users"
    user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_utils.uuid7)
    role: Mapped[user_roles] = mapped_column(Enum("teacher", "admin", "student", name="user_roles"), nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password_hash: Mapped[str|None] = mapped_column(String,nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=text('now()'), nullable=False)

# students <-> class many-to-many relation 
student_class_association = Table(
    "student_class",
    Base.metadata,
    Column("student_id", ForeignKey("students.roll_num", ondelete="CASCADE"), primary_key=True),
    Column("class_id", ForeignKey("classes.class_id", ondelete="CASCADE"), primary_key=True),
)
    
class Students(Base):
    __tablename__="students"
    user_id: Mapped[UUID]=mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, unique=True)
    name: Mapped[str]=mapped_column(String, nullable=False)
    roll_num: Mapped[str]=mapped_column(String, primary_key=True)
    email: Mapped[str]=mapped_column(String, nullable=True, unique=True)
    enrolled_classes: Mapped[List["Class"]]=relationship(secondary=student_class_association, back_populates="enrolled_students")
    created_at: Mapped[datetime]=mapped_column(TIMESTAMP(timezone=True), server_default=text('now()'), nullable=False)
    
class Class(Base):
    __tablename__="classes"
    class_id: Mapped[UUID]=mapped_column(UUID(as_uuid=True), primary_key=True)
    class_name: Mapped[str]=mapped_column(String, nullable=False, unique=True)
    batch_start_year: Mapped[int]=mapped_column(INTEGER, nullable=False)
    curr_year: Mapped[int]=mapped_column(INTEGER, nullable=False)
    course_id: Mapped[str]=mapped_column(String, nullable=False)
    department: Mapped[str]=mapped_column(String, nullable=True)
    branch: Mapped[str]=mapped_column(String, nullable=False)
    enrolled_students: Mapped[List["Students"]]=relationship(secondary=student_class_association, back_populates="enrolled_classes")
    __table_args__=(
        UniqueConstraint("batch_start_year", "curr_year", "branch", "course_id", name="batch_curr_year_branch_course"),  # there can't be 2 classes of same subject/course in the same year for the same branch and for same batch 
    )
    
    
class Teacher(Base):
    __tablename__="teachers"
    user_id: Mapped[UUID]=mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True)
    name: Mapped[str]=mapped_column(String, nullable=False)
    email: Mapped[str]=mapped_column(String, nullable=False, unique=True)
    department: Mapped[str]=mapped_column(String, nullable=False)
    created_at: Mapped[datetime]=mapped_column(TIMESTAMP(timezone=True), server_default=text('now()'), nullable=False)
    
class Admin(Base):
    __tablename__="admins"
    user_id: Mapped[UUID]=mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True)
    name: Mapped[str]=mapped_column(String, nullable=False)
    email: Mapped[str]=mapped_column(String, nullable=False, unique=True)
    created_at: Mapped[datetime]=mapped_column(TIMESTAMP(timezone=True), server_default=text('now()'), nullable=False)
    
class Attendance(Base):
    __tablename__="attendance"
    attendance_id: Mapped[UUID]=mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_utils.uuid7)
    class_id: Mapped[UUID]=mapped_column(UUID(as_uuid=True), ForeignKey("classes.class_id", ondelete="CASCADE"), nullable=False)
    student_roll: Mapped[str]=mapped_column(String, ForeignKey("students.roll_num", ondelete="CASCADE"), nullable=False)
    attendance_date: Mapped[date]=mapped_column(Date, server_default=text("CURRENT_DATE"),nullable=False)
    __table_args__=(
        UniqueConstraint("student_roll", "attendance_date", "class_id", name="studentId_attendanceDate"),
    )