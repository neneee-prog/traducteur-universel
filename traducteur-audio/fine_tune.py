import os
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, Trainer, TrainingArguments
from datasets import Dataset
import pandas as pd

# Charger le modèle et le tokenizer pour le fine-tuning
marian_model_name = "Helsinki-NLP/opus-mt-en-fr"
model = AutoModelForSeq2SeqLM.from_pretrained(marian_model_name)
tokenizer = AutoTokenizer.from_pretrained(marian_model_name)

# Préparer les données pour le fine-tuning
def preprocess_function(examples):
    inputs = [str(ex) for ex in examples['transcription']]
    targets = [str(ex) for ex in examples['translation']]
    model_inputs = tokenizer(inputs, max_length=128, truncation=True, padding="max_length")
    labels = tokenizer(targets, max_length=128, truncation=True, padding="max_length")
    model_inputs["labels"] = labels["input_ids"]
    return model_inputs

# Charger et préparer les datasets d'entraînement et d'évaluation
base_dir = os.path.dirname(os.path.abspath(__file__))
train_dataset_path = os.path.join(base_dir, 'train_dataset.csv')
eval_dataset_path = os.path.join(base_dir, 'eval_dataset.csv')

train_df = pd.read_csv(train_dataset_path, sep=';')
eval_df = pd.read_csv(eval_dataset_path, sep=';')

train_dataset = Dataset.from_pandas(train_df)
eval_dataset = Dataset.from_pandas(eval_df)

tokenized_train_dataset = train_dataset.map(preprocess_function, batched=True)
tokenized_eval_dataset = eval_dataset.map(preprocess_function, batched=True)

# Définir les arguments d'entraînement
training_args = TrainingArguments(
    output_dir="./results",
    eval_strategy="epoch",
    learning_rate=2e-5,
    per_device_train_batch_size=4,
    per_device_eval_batch_size=4,
    num_train_epochs=3,
    weight_decay=0.01,
)

# Initialiser le Trainer avec les datasets d'entraînement et d'évaluation
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_train_dataset,
    eval_dataset=tokenized_eval_dataset,
)

# Effectuer le fine-tuning
trainer.train()

# Sauvegarder le modèle fine-tuné
model.save_pretrained("./fine-tuned-model")
tokenizer.save_pretrained("./fine-tuned-model")
