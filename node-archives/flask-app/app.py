from flask import Flask, request, jsonify
import pyaudio
import wave
import json
from vosk import Model, KaldiRecognizer
from transformers import MarianMTModel, MarianTokenizer
import torch
import requests
import os
from dotenv import load_dotenv
from collections import deque

# Charge les variables d'environnement du fichier .env
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

app = Flask(__name__)

# Configuration des chemins des modèles
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_EN_PATH = os.path.join(BASE_DIR, '..', 'traducteur-audio', 'models', 'vosk-model-small-en-us-0.15')

# Chargement du modèle Vosk
try:
    model_en = Model(MODEL_EN_PATH)
    print(f"Modèle Vosk EN chargé depuis : {MODEL_EN_PATH}")
except Exception as e:
    print(f"Erreur modèle Vosk : {str(e)}")
    exit(1)

# Configuration de la traduction
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
MARIAN_MODEL_NAME = "Helsinki-NLP/opus-mt-en-fr"
marian_tokenizer = MarianTokenizer.from_pretrained(MARIAN_MODEL_NAME)
marian_model = MarianMTModel.from_pretrained(MARIAN_MODEL_NAME).to(DEVICE)

# Paramètres audio
CHUNK = 20000
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000

# Initialisation PyAudio
p = pyaudio.PyAudio()
stream = p.open(
    format=FORMAT,
    channels=CHANNELS,
    rate=RATE,
    input=True,
    frames_per_buffer=CHUNK
)

# Buffer audio circulaire
audio_buffer = deque(maxlen=50)

# Initialisation du reconnaisseur Vosk
rec_en = KaldiRecognizer(model_en, RATE)

# Variables globales pour accumuler les résultats
current_transcription = ""
current_translation = ""

def correct_and_translate(text):
    global current_translation
    API_KEY = os.getenv("OPENAI_API_KEY")  # Récupère la clé depuis .env

    if not API_KEY:
        raise ValueError("OPENAI_API_KEY non trouvée dans .env")

    try:
        # Correction avec GPT
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "gpt-3.5-turbo-instruct",
            "prompt": f"Correct and add punctuation: '{text}'",
            "max_tokens": 150,
            "temperature": 0.7
        }
        response = requests.post(
            "https://api.openai.com/v1/completions",
            headers=headers,
            json=data,
            timeout=10
        )
        response.raise_for_status()  # Lève une erreur pour les codes HTTP 4xx/5xx

        corrected_text = response.json()["choices"][0]["text"].strip()

        # Traduction avec MarianMT
        tokenized = marian_tokenizer(
            [corrected_text],
            return_tensors="pt",
            padding=True,
            truncation=True
        ).to(DEVICE)
        translation = marian_model.generate(**tokenized)
        translated_text = marian_tokenizer.decode(
            translation[0],
            skip_special_tokens=True
        )

        current_translation = translated_text
        return translated_text

    except Exception as e:
        print(f"Erreur de traduction : {str(e)}")
        return ""

@app.route('/process-audio', methods=['POST'])
def process_audio():
    global current_transcription, current_translation
    try:
        audio_file = request.files['audio']
        temp_path = os.path.join(BASE_DIR, 'temp_audio.wav')
        audio_file.save(temp_path)

        with wave.open(temp_path, "rb") as wf:
            while True:
                data = wf.readframes(CHUNK)
                if len(data) == 0:
                    break
                audio_buffer.append(data)
                if rec_en.AcceptWaveform(data):
                    result = json.loads(rec_en.Result())
                    current_transcription += " " + result.get("text", "")

        # Traduction finale
        current_translation = correct_and_translate(current_transcription)
        current_transcription = ""  # Réinitialisation

        os.remove(temp_path)
        return jsonify({'translatedText': current_translation})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
