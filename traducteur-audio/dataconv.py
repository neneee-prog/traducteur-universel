import os
import csv

# Chemin vers le répertoire extrait
extracted_dir = 'opus_datasets/extracted/LibriTTS_R/dev-other'

# Chemin vers le fichier CSV de sortie
output_csv = '../dataset.csv'

# Fonction pour lire les fichiers de transcription
def process_transcription_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read().strip()  # Lire tout le contenu comme transcription

# Créer le fichier CSV avec les en-têtes
with open(output_csv, mode='w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file, delimiter=';')
    writer.writerow(["audio_file", "transcription", "translation"])

# Ouvrir le fichier CSV en mode ajout avec des points-virgules comme séparateurs
with open(output_csv, mode='a', newline='', encoding='utf-8') as file:
    writer = csv.writer(file, delimiter=';')

    # Parcourir les répertoires et fichiers dans le répertoire extrait
    for root, dirs, files in os.walk(extracted_dir):
        for filename in files:
            if filename.endswith(".wav"):  # Traiter uniquement les fichiers audio
                audio_path = os.path.join(root, filename)
                base_name = os.path.splitext(filename)[0]

                # Trouver le fichier de transcription correspondant
                transcription_file = f"{base_name}.normalized.txt"
                transcription_path = os.path.join(root, transcription_file)

                if os.path.exists(transcription_path):
                    transcription = process_transcription_file(transcription_path)
                    translation = ""  # Vous pouvez ajouter une traduction si nécessaire
                    writer.writerow([audio_path, transcription, translation])
                    print(f"Ajouté: {audio_path}, {transcription}, {translation}")
                else:
                    print(f"Aucun fichier de transcription trouvé pour {audio_path}")

print("Données ajoutées avec succès.")
