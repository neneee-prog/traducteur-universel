from fastapi import APIRouter, HTTPException 
from pydantic import BaseModel
from core.security import create_access_token
from models.firestore_db import create_user_firestore, get_user_firestore
import hashlib

router = APIRouter(prefix="/api/auth", tags=["auth"])

class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

@router.post("/register", name="register_user")
async def register_user(req: RegisterRequest):
    if get_user_firestore(req.email):
        raise HTTPException(status_code=400, detail="User already exists")
    hashed_pw = hash_password(req.password)
    user_data = {"name": req.name, "email": req.email, "password": hashed_pw}
    create_user_firestore(user_data)
    return {"message": "User registered successfully", "user": {"name": req.name, "email": req.email}}

@router.post("/login", name="login_user")
async def login_user(req: LoginRequest):
    user = get_user_firestore(req.email)
    if not user or hash_password(req.password) != user["password"]:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": req.email})
    return {"token": token, "user": {"email": req.email, "name": user["name"]}}


