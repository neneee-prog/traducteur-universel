# Dockerfile

FROM python:3.10-slim

# Installation des dépendances système
RUN apt-get update && apt-get install -y \
    build-essential \
    portaudio19-dev \
    libsndfile1 \
    libpython3-dev \
    libasound2-dev \
    curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Installer les dépendances Python
COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copier les fichiers essentiels
COPY .env ./
COPY firebase-credentials.json ./
COPY traducteur-audio/ ./traducteur-audio/
COPY public/ ./public/

# Supprimer ou commenter la ligne suivante pour ne pas forcer le port
# ENV PORT=8081

# Optionnel : Exposer le port (pour info)
EXPOSE 8080

# Lancer uvicorn en utilisant la variable d'environnement $PORT, ou 8080 par défaut
CMD ["sh", "-c", "uvicorn traducteur-audio.app:app --host 0.0.0.0 --port ${PORT:-8080}"]
