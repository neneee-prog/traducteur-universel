import pandas as pd
from sklearn.model_selection import train_test_split

# Charger le dataset
dataset_path = 'C:/Users/ASUS/Desktop/traducteur-universel/traducteur-audio/dataset.csv'
df = pd.read_csv(dataset_path, sep=';')

# Diviser le dataset en ensembles d'entraînement et de validation
train_df, eval_df = train_test_split(df, test_size=0.15, random_state=42)

# Sauvegarder les ensembles d'entraînement et de validation
train_df.to_csv('C:/Users/ASUS/Desktop/traducteur-universel/traducteur-audio/train_dataset.csv', index=False, sep=';')
eval_df.to_csv('C:/Users/ASUS/Desktop/traducteur-universel/traducteur-audio/eval_dataset.csv', index=False, sep=';')

print("Datasets créés avec succès.")

