# traducteur-audio/utils/translation.py
import re
import torch
from transformers import MarianMTModel, MarianTokenizer

def post_process_translation(text: str) -> str:
    text = text.strip()
    if not text:
        return text
    text = text[0].upper() + text[1:]
    text = re.sub(r'\.\s+([a-z])', lambda m: '. ' + m.group(1).upper(), text)
    return text

def init_marian_model(model_name: str, device):
    model = MarianMTModel.from_pretrained(model_name).to(device)
    tokenizer = MarianTokenizer.from_pretrained(model_name)
    return model, tokenizer

def translate_text(text: str, model, tokenizer, device) -> str:
    with torch.no_grad():
        tokenized = tokenizer.encode(text, return_tensors="pt", padding=True, truncation=True).to(device)
        translation_tokens = model.generate(tokenized, num_beams=5, do_sample=False, early_stopping=True)
        translated = tokenizer.decode(translation_tokens[0], skip_special_tokens=True)
    return post_process_translation(translated)

