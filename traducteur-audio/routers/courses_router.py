from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/courses", tags=["courses"])

class Course(BaseModel):
    id: int
    name: str

COURSES = [
    {"id": 1, "name": "Cours de Traduction"},
    {"id": 2, "name": "Cours Avancé"}
]

@router.get("/", name="list_courses")
async def list_courses():
    return COURSES

class CreateCourseRequest(BaseModel):
    name: str

@router.post("/", name="create_course")
async def create_course(req: CreateCourseRequest):
    new_course = {"id": len(COURSES) + 1, "name": req.name}
    COURSES.append(new_course)
    return new_course

@router.patch("/{course_id}", name="update_course")
async def update_course(course_id: int, req: CreateCourseRequest):
    for course in COURSES:
        if course["id"] == course_id:
            course["name"] = req.name
            return course
    raise HTTPException(status_code=404, detail="Course not found")

@router.delete("/{course_id}", name="delete_course")
async def delete_course(course_id: int):
    global COURSES
    COURSES = [course for course in COURSES if course["id"] != course_id]
    return {"message": f"Course {course_id} deleted."}