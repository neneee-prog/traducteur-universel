# traducteur-audio/Dockerfile

FROM python:3.10-slim

# Installer les dépendances système pour PyAudio/Vosk
RUN apt-get update && apt-get install -y \
    build-essential \
    portaudio19-dev \
    libsndfile1 \
    libpython3-dev \
    libasound2-dev \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copier et installer les dépendances Python
COPY ../requirements.txt ./
RUN pip install --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# Copier le code de l’application
COPY app.py ./

# Copier le dossier des modèles (vosk-model-small-en-us-0.15)
COPY models ./models

# Copier les assets statiques pour Flask
COPY ../public ./public

# Exposer le port Cloud Run attend (8080)
EXPOSE 8080

# Lancer l’application
CMD ["python", "app.py"]
