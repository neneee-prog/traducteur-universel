import asyncio
import websockets
import torch
from TTS.api import TTS
import sounddevice as sd
import numpy as np

# Initialiser TTS avec un modèle pour le français
device = "cuda" if torch.cuda.is_available() else "cpu"
tts = TTS("tts_models/fr/css10/vits").to(device)

# Fonction pour générer et diffuser l'audio en temps réel
async def audio_stream(websocket, path):
    try:
        # Exemple de texte à synthétiser
        text = "Bonjour, ceci est un test de synthèse vocale en temps réel."

        # Générer l'audio
        wav = tts.tts(text, speaker_wav=None, language="fr")

        # Convertir l'audio en tableau numpy
        audio_array = np.array(wav)

        # Définir le flux audio
        stream = sd.OutputStream(samplerate=22050, channels=1)
        stream.start()

        # Envoyer les morceaux d'audio
        chunk_size = 512  # Réduire la taille des chunks pour diminuer la latence
        for i in range(0, len(audio_array), chunk_size):
            chunk = audio_array[i:i+chunk_size]
            stream.write(chunk)
            await websocket.send(chunk.tobytes())

        stream.stop()
    except websockets.ConnectionClosed:
        print("Connection closed")
    except Exception as e:
        print(f"Error: {e}")

async def main():
    print("Starting WebSocket server...")
    async with websockets.serve(audio_stream, "localhost", 8765):
        await asyncio.Future()  # Maintenir le serveur en cours d'exécution

# Exécuter la boucle d'événements
if __name__ == "__main__":
    asyncio.run(main())
