import os
from google.cloud import firestore

def get_firestore_client():
    """
    Retourne un client Firestore.
    Assurez-vous que la variable d'environnement GOOGLE_APPLICATION_CREDENTIALS est bien définie.
    """
    return firestore.Client()

def create_user_firestore(user_data: dict):
    """
    Crée un document dans la collection "users" avec l'email comme identifiant unique.
    """
    client = get_firestore_client()
    doc_ref = client.collection("users").document(user_data["email"])
    doc_ref.set(user_data)
    return user_data

def get_user_firestore(email: str):
    """
    Récupère les données d'un utilisateur depuis Firestore.
    """
    client = get_firestore_client()
    doc_ref = client.collection("users").document(email)
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict()
    return None

def update_user_firestore(email: str, updates: dict):
    """
    Met à jour les informations d'un utilisateur.
    """
    client = get_firestore_client()
    doc_ref = client.collection("users").document(email)
    doc_ref.update(updates)
    return get_user_firestore(email)
def create_translation(text: str):
    """Crée un document dans la collection 'translations'."""
    client = get_firestore_client()
    doc_ref = client.collection("translations").document()  # auto-ID
    doc_ref.set({"text": text})
    return doc_ref.id

def list_translations():
    """Récupère toutes les traductions de la collection 'translations'."""
    client = get_firestore_client()
    docs = client.collection("translations").stream()
    results = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        results.append(data)
    return results
