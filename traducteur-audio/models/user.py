# traducteur-audio/models/user.py
from pydantic import BaseModel

class User(BaseModel):
    id: int
    name: str
    email: str


