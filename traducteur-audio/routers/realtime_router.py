import json
import time
import threading
import queue
import re
import asyncio
import os
import requests
import numpy as np

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from deepmultilingualpunctuation import PunctuationModel
from vosk import Model as VoskModel, KaldiRecognizer
import pyaudio
import torch

# Option pour choisir le moteur de traduction
USE_OPENAI = True

if USE_OPENAI:
    import openai
    openai.api_key = os.getenv("OPENAI_API_KEY")

router = APIRouter(prefix="/api/realtime", tags=["realtime"])

CHUNK = 30000
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
PAUSE_THRESHOLD = 4.0  # secondes de silence pour finaliser

# Seuil RMS (amplitude minimale) pour considérer qu'il y a de la parole
RMS_THRESHOLD = 500

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# --- Chargement des modèles ---
# Assurez-vous que le chemin correspond à votre structure (par exemple dans Docker)
vosk_model = VoskModel("models/vosk-model-small-en-us-0.15")
recognizer = KaldiRecognizer(vosk_model, RATE)

punc_model = PunctuationModel()

# Initialiser PyAudio
p = pyaudio.PyAudio()
stream = p.open(
    format=FORMAT,
    channels=CHANNELS,
    rate=RATE,
    input=True,
    frames_per_buffer=CHUNK
)

translation_queue = queue.Queue()
ws_queue = queue.Queue()

listening = True
recording = False  # Contrôle de l'enregistrement via commande WebSocket
accumulated_text = ""
last_update_time = time.time()

def compute_rms(audio_data):
    """Calcule la valeur RMS du segment audio."""
    samples = np.frombuffer(audio_data, dtype=np.int16)
    if samples.size == 0:
        return 0
    rms = np.sqrt(np.mean(samples.astype(np.float32) ** 2))
    return rms

def post_process_translation(text: str) -> str:
    """Applique une majuscule initiale et corrige la ponctuation simple."""
    text = text.strip()
    if not text:
        return text
    text = text[0].upper() + text[1:]
    text = re.sub(r'\.\s+([a-z])', lambda m: '. ' + m.group(1).upper(), text)
    return text

def process_audio():
    """
    Lit le micro en continu uniquement si 'recording' est True.
    Avant de traiter, le niveau sonore (RMS) est vérifié.
    Après PAUSE_THRESHOLD secondes de silence, le texte accumulé est envoyé à translation_queue.
    """
    global accumulated_text, last_update_time, recording
    while listening:
        if not recording:
            time.sleep(0.1)
            continue

        data = stream.read(CHUNK)
        # Calculer l'amplitude RMS et ignorer si trop faible
        rms = compute_rms(data)
        if rms < RMS_THRESHOLD:
            # Pas assez de signal pour considérer qu'il y a de la parole
            time.sleep(0.01)
            continue

        if recognizer.AcceptWaveform(data):
            result = json.loads(recognizer.Result())
            final_text = result.get("text", "").strip()
            if final_text:
                accumulated_text += " " + final_text
            last_update_time = time.time()
        else:
            partial = json.loads(recognizer.PartialResult()).get("partial", "").strip()

        if accumulated_text and (time.time() - last_update_time >= PAUSE_THRESHOLD):
            text_to_translate = accumulated_text.strip()
            print(f"(Inactivity) Finalizing: {text_to_translate}")
            # Filtrer les segments trop courts (ici au moins 5 mots)
            if len(text_to_translate.split()) >= 5:
                translation_queue.put(text_to_translate)
            else:
                print("Segment trop court, on ignore =>", text_to_translate)
            accumulated_text = ""
        time.sleep(0.01)

def translate_text_openai(text):
    """
    Utilise l'API OpenAI pour traduire le texte en français.
    Le prompt demande une traduction naturelle sans explication ni commentaire.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise Exception("OPENAI_API_KEY non défini dans l'environnement.")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": "You are a translation assistant."},
            {"role": "user", "content": (
                "Translate the following English text into French. Do not translate word by word; provide a natural, fluent translation that respects proper punctuation and grammar. "
                "Return ONLY the final translated text without any additional commentary or explanation:\n\n"
                f"'''{text}'''"
            )}
        ],
        "temperature": 0.3,
        "max_tokens": 512
    }
    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data)
    if response.status_code == 200:
        result = response.json()
        translated = result["choices"][0]["message"]["content"].strip()
        translated = translated.strip(' "\'')
        return translated
    else:
        raise Exception(f"Erreur API OpenAI: {response.status_code} - {response.text}")

def translation_worker():
    """
    Récupère le texte depuis translation_queue, le nettoie et le traduit en utilisant l'API OpenAI.
    Le résultat est placé dans ws_queue.
    """
    while listening:
        try:
            text = translation_queue.get(timeout=0.1)
            clean_text = re.sub(r'\b(um|uh|you know)\b', '', text, flags=re.IGNORECASE).strip()
            if USE_OPENAI:
                translated = translate_text_openai(clean_text)
            else:
                translated = clean_text  # Placeholder pour MarianMT si nécessaire
            final_output = post_process_translation(translated)
            print(f"Translated: {final_output}")
            ws_queue.put(final_output)
        except queue.Empty:
            continue

def clear_queues():
    """Réinitialise les files d'attente et l'accumulation."""
    global accumulated_text, translation_queue, ws_queue
    translation_queue = queue.Queue()
    ws_queue = queue.Queue()
    accumulated_text = ""

# Lancer les threads pour le traitement audio et la traduction
threading.Thread(target=process_audio, daemon=True).start()
threading.Thread(target=translation_worker, daemon=True).start()

class ConnectionManager:
    """Gestion des connexions WebSocket."""
    def __init__(self):
        self.active_connections = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

manager = ConnectionManager()

@router.websocket("/ws")
async def realtime_ws(websocket: WebSocket):
    """
    WebSocket : gère la communication avec le client.
    - Reçoit les commandes "start" et "stop" pour contrôler l'enregistrement.
    - Lors de "stop", vide les files d'attente pour éviter le traitement des segments en attente.
    - Envoie au client les textes traduits depuis ws_queue.
    """
    await manager.connect(websocket)
    print("Client connected to /api/realtime/ws")
    
    try:
        while True:
            try:
                message = await asyncio.wait_for(websocket.receive_text(), timeout=0.1)
                message = message.strip().lower()
                if message == "start":
                    global recording
                    recording = True
                    print("Recording started.")
                elif message == "stop":
                    recording = False
                    print("Recording stopped.")
                    clear_queues()
            except asyncio.TimeoutError:
                pass

            try:
                text = ws_queue.get(timeout=0.2)
                await websocket.send_text(text)
            except queue.Empty:
                pass

            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("Client disconnected from /api/realtime/ws")
    except Exception as e:
        manager.disconnect(websocket)
        print(f"WebSocket error: {e}")
