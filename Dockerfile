FROM python:3.10-slim

# Installer les dépendances système
RUN apt-get update && apt-get install -y \
      build-essential \
      portaudio19-dev \
      libsndfile1 \
      libpython3-dev \
      libasound2-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copier les dépendances Python depuis la racine
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copier le code et les modèles
COPY traducteur-audio/app.py ./
COPY traducteur-audio/models/ ./models/
COPY public/ ./public/

EXPOSE 8080

CMD ["python", "app.py"]

