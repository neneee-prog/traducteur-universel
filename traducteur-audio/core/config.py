# traducteur-audio/core/config.py
import os
from dotenv import load_dotenv

load_dotenv()  # Charge le fichier .env

class Settings:
    SECRET_KEY = os.getenv("SECRET_KEY", "votre-cle-secrete-par-defaut")
    ALGORITHM = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
    PORT = int(os.getenv("PORT", 8081))
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")

settings = Settings()

