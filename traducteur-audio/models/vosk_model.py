# traducteur-audio/models/vosk_model.py
import os
from vosk import Model as VoskModel, KaldiRecognizer

def load_vosk_model():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(base_dir, '..', 'models', 'vosk-model-small-en-us-0.15')
    model = VoskModel(model_path)
    recognizer = KaldiRecognizer(model, 16000)
    return model, recognizer

