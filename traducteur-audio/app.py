import logging
import warnings
import os
import json
import threading
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_socketio import SocketIO, emit
from vosk import Model, KaldiRecognizer
from transformers import MarianMTModel, MarianTokenizer
import pyaudio
from pymongo import MongoClient
from bson.objectid import ObjectId
from dotenv import load_dotenv

warnings.filterwarnings("ignore", message="ALSA lib")
load_dotenv()

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__, static_folder='public', template_folder='public/html')
app.secret_key = os.getenv("SECRET_KEY")
app.config.update({
    'SESSION_COOKIE_HTTPONLY': True,
    'SESSION_COOKIE_SAMESITE': 'Lax',
    'SESSION_COOKIE_SECURE': True
})

socketio = SocketIO(app, cors_allowed_origins="*", logger=True)

client = MongoClient(os.getenv("MONGO_URI"), serverSelectionTimeoutMS=5000)
try:
    client.admin.command('ping')
    logging.info("Connexion à MongoDB réussie.")
except Exception as e:
    logging.error(f"MongoDB Error: {e}")
db = client.traducteur_universel

MODEL_EN_PATH = os.path.join(os.path.dirname(__file__), 'models', 'vosk-model-small-en-us-0.15')
model_en = Model(MODEL_EN_PATH)

marian_tokenizer = MarianTokenizer.from_pretrained("Helsinki-NLP/opus-mt-en-fr")
marian_model = MarianMTModel.from_pretrained("Helsinki-NLP/opus-mt-en-fr").to('cpu')

CHUNK, FORMAT, CHANNELS, RATE = 20000, pyaudio.paInt16, 1, 16000
audio = pyaudio.PyAudio()
rec_en = KaldiRecognizer(model_en, RATE)
audio_buffer = []
audio_lock = threading.Lock()
is_recording = False

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/app')
def app_page():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('app.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        user = db.users.find_one({"email": request.form['email'], "password": request.form['password']})
        if user:
            session['user_id'] = str(user['_id'])
            return redirect(url_for('app_page'))
        return redirect(url_for('error'))
    return render_template('login.html')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        if not db.users.find_one({"email": request.form['email']}):
            db.users.insert_one({
                "name": request.form['name'],
                "email": request.form['email'],
                "password": request.form['password']
            })
            return redirect(url_for('login'))
        return redirect(url_for('error'))
    return render_template('register.html')

@app.route('/terms')
def terms(): return render_template('terms.html')
@app.route('/policy')
def policy(): return render_template('policy.html')
@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('profile.html')
@app.route('/error')
def error(): return render_template('error.html')

@app.route('/submit-translation', methods=['POST'])
def submit_translation():
    if 'user_id' not in session:
        return jsonify({"error":"Authentification requise"}),401
    db.translations.insert_one({
        "original_text": request.json['text'],
        "translated_text": request.json['text'],
        "user_id": ObjectId(session['user_id']),
        "timestamp": datetime.utcnow()
    })
    return jsonify({"status":"success"})

@app.route('/api/courses', methods=['GET','POST'])
def courses():
    if request.method=='GET':
        return jsonify([{"id": str(c["_id"]), "name": c["name"]} for c in db.courses.find({},{"name":1})])
    data=request.json
    r=db.courses.insert_one({"name":data['name']})
    return jsonify({"id":str(r.inserted_id),"name":data['name']})

@socketio.on('start_recording')
def start_rec():
    global is_recording
    is_recording=True
    threading.Thread(target=audio_processing).start()

@socketio.on('audio_data')
def recv_audio(blob):
    with audio_lock: audio_buffer.append(blob)

@socketio.on('stop_recording')
def stop_rec():
    global is_recording
    is_recording=False

def audio_processing():
    while is_recording:
        with audio_lock:
            if audio_buffer:
                data=audio_buffer.pop(0)
                if rec_en.AcceptWaveform(data):
                    text=json.loads(rec_en.Result()).get('text','')
                    process_translation(text)
                else:
                    text=json.loads(rec_en.PartialResult()).get('partial','')
                    process_translation(text)

def process_translation(text):
    if text.strip():
        translated=translate_text(text)
        emit('translation',{'translatedText':translated},broadcast=True)

def translate_text(text):
    tok=marian_tokenizer([text],return_tensors="pt",truncation=True)
    return marian_tokenizer.decode(marian_model.generate(**tok)[0],skip_special_tokens=True)

if __name__=='__main__':
    socketio.run(app,host='0.0.0.0',port=int(os.getenv("PORT",8080)),debug=False)
