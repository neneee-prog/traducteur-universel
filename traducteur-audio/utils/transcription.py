# traducteur-audio/utils/transcription.py
import json, torch
from vosk import Model as VoskModel, KaldiRecognizer
import pyaudio

CHUNK = 20000
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000

def init_vosk_model(model_path: str):
    model = VoskModel(model_path)
    recognizer = KaldiRecognizer(model, RATE)
    return model, recognizer

def transcribe_stream(recognizer, stream):
    data = stream.read(CHUNK)
    if recognizer.AcceptWaveform(data):
        result = json.loads(recognizer.Result())
        return result.get("text", "").strip()
    else:
        partial = json.loads(recognizer.PartialResult()).get("partial", "").strip()
        return partial

