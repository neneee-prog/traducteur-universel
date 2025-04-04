# traducteur-audio/utils/tts.py
import time
import torch
import sounddevice as sd

def load_silero_tts_model():
    output = torch.hub.load(
        repo_or_dir="snakers4/silero-models",
        model="silero_tts",
        language="fr",
        speaker="v3_fr",
        trust_repo=True
    )
    if isinstance(output, (tuple, list)) and len(output) == 4:
        silero_model, example_text, languages, speaker_ids = output
    else:
        silero_model, example_text = output
        languages = ["fr"]
        speaker_ids = {"v3_fr": None}
    return silero_model, languages, speaker_ids

silero_model, languages, speaker_ids = load_silero_tts_model()
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
silero_model.to(device)

def tts_speak(text: str, sample_rate: int = 48000, speaker: str = "v3_fr"):
    audio_output = silero_model.apply_tts(text, speaker=speaker, sample_rate=sample_rate)
    sd.play(audio_output, sample_rate)
    sd.wait()
