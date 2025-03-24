import express from 'express';
import mongoose from 'mongoose';
import bodyParser from 'body-parser';
import bcrypt from 'bcrypt';
import jwt from 'jsonwebtoken';
import { body, validationResult } from 'express-validator';
import { pipeline } from '@xenova/transformers';
import vosk from 'vosk';
const { Model, KaldiRecognizer } = vosk;
import fs from 'fs';
import path from 'path';
import axios from 'axios';
import { WebSocketServer } from 'ws';
import http from 'http';

const app = express();
app.use(bodyParser.json());

// Connexion MongoDB avec retry
const connectWithRetry = async () => {
  try {
    await mongoose.connect(process.env.MONGO_URI, {
      serverSelectionTimeoutMS: 5000,
      retryWrites: true
    });
    console.log("MongoDB connecté");
  } catch (error) {
    console.error("Échec connexion MongoDB, retry dans 5s...");
    setTimeout(connectWithRetry, 5000);
  }
};
connectWithRetry();

// Configuration des modèles Vosk
const modelEnPath = path.join(process.cwd(), 'traducteur-audio', 'models', 'vosk-model-small-en-us-0.15');
const modelFrPath = path.join(process.cwd(), 'traducteur-audio', 'models', 'vosk-model-small-fr-0.22');
// Chargement des modèles Vosk
let modelEn, modelFr;
try {
    modelEn = new Model(modelEnPath);
    modelFr = new Model(modelFrPath);
    console.log('Modèles Vosk chargés avec succès');
} catch (err) {
    console.error('Erreur Vosk:', err.message);
    process.exit(1);
}

// Pipeline de traduction
const translator = await pipeline('translation', 'Helsinki-NLP/opus-mt-en-fr');

// Fonction de transcription audio
function transcribeAudio(audioFilePath, model) {
    const wf = fs.createReadStream(audioFilePath);
    const rec = new KaldiRecognizer(model, wf.getframerate());

    return new Promise((resolve, reject) => {
        rec.on('result', (result) => resolve(result.text));
        rec.on('error', (error) => reject(error));
        wf.pipe(rec);
    });
}

// Endpoint transcription/traduction
app.post('/transcribe-and-translate', async (req, res) => {
    const { audioFile } = req.body;
    try {
        const transcribedTextEn = await transcribeAudio(audioFile, modelEn);
        const translatedTextFr = (await translator(transcribedTextEn))[0].translation_text;
        res.json({ transcribedTextEn, translatedTextFr });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Endpoint traitement audio Python
app.post('/process-audio', async (req, res) => {
    const { audioData } = req.body;
    try {
        const response = await axios.post('http://host.docker.internal:5000/process-audio', { audioData });
        res.json(response.data);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Schéma utilisateur
const userSchema = new mongoose.Schema({
    name: String,
    email: String,
    password: String
});
const User = mongoose.model('User', userSchema);

// Validation inscription
const registerValidation = [
    body('name').notEmpty().withMessage('Nom requis'),
    body('email').isEmail().withMessage('Email invalide'),
    body('password').isLength({ min: 6 }).withMessage('Mot de passe trop court')
];

app.post('/register', registerValidation, async (req, res) => {
    const errors = validationResult(req);
    if (!errors.isEmpty()) return res.status(400).json({ errors: errors.array() });

    try {
        const hashedPassword = await bcrypt.hash(req.body.password, 10);
        const user = new User({
            name: req.body.name,
            email: req.body.email,
            password: hashedPassword
        });
        await user.save();
        res.status(201).send('Utilisateur créé');
    } catch (error) {
        res.status(500).send('Erreur inscription');
    }
});

// Connexion utilisateur
app.post('/login', async (req, res) => {
    try {
        const user = await User.findOne({ email: req.body.email });
        if (!user) return res.status(400).send('Utilisateur inconnu');

        const validPassword = await bcrypt.compare(req.body.password, user.password);
        if (!validPassword) return res.status(400).send('Mot de passe incorrect');

        const token = jwt.sign({ userId: user._id }, 'votre_clé_secrète', { expiresIn: '1h' });
        res.header('auth-token', token).send(token);
    } catch (error) {
        res.status(500).send('Erreur connexion');
    }
});

// Middleware d'authentification
const authMiddleware = (req, res, next) => {
    const authHeader = req.header('Authorization');
    if (!authHeader?.startsWith('Bearer ')) return res.status(401).send('Accès refusé');

    const token = authHeader.split(' ')[1];
    jwt.verify(token, 'votre_clé_secrète', (err, decoded) => {
        if (err) return res.status(401).send('Token invalide');
        req.userId = decoded.userId;
        next();
    });
};

// Endpoint ID utilisateur
app.get('/user-id', authMiddleware, (req, res) => {
    res.status(200).json({ userId: req.userId });
});

// Schéma traduction
const translationSchema = new mongoose.Schema({
    userId: { type: mongoose.Schema.Types.ObjectId, ref: 'User', required: true },
    originalText: String,
    translatedText: String,
    sourceLanguage: String,
    targetLanguage: String,
    timestamp: { type: Date, default: Date.now }
});
const Translation = mongoose.model('Translation', translationSchema);

// Validation traduction
const translationValidation = [
    body('originalText').notEmpty().withMessage('Texte original requis'),
    body('translatedText').notEmpty().withMessage('Traduction requise'),
    body('sourceLanguage').notEmpty().withMessage('Langue source requise'),
    body('targetLanguage').notEmpty().withMessage('Langue cible requise')
];

// Soumission traduction
app.post('/submit-translation', authMiddleware, translationValidation, async (req, res) => {
    const errors = validationResult(req);
    if (!errors.isEmpty()) return res.status(400).json({ errors: errors.array() });

    try {
        const { originalText, translatedText, sourceLanguage, targetLanguage } = req.body;
        const newTranslation = new Translation({
            userId: req.userId,
            originalText,
            translatedText,
            sourceLanguage,
            targetLanguage
        });
        await newTranslation.save();
        res.status(201).send('Traduction soumise');
    } catch (error) {
        res.status(500).send('Erreur soumission');
    }
});

// Récupération traductions
app.get('/translations/:userId', authMiddleware, async (req, res) => {
    try {
        if (req.userId !== req.params.userId) return res.status(403).send('Accès interdit');
        const translations = await Translation.find({ userId: req.params.userId });
        res.status(200).json(translations);
    } catch (error) {
        res.status(500).send('Erreur récupération');
    }
});

// Serveur WebSocket
const server = http.createServer(app);
const wss = new WebSocketServer({ server });

wss.on('connection', (ws) => {
    ws.on('message', (message) => {
        wss.clients.forEach(client => {
            if (client !== ws && client.readyState === WebSocketServer.OPEN) {
                client.send(message.toString());
            }
        });
    });
});

// Démarrage serveur
const PORT = process.env.PORT || 3000;
server.listen(PORT, () => {
    console.log(`Serveur démarré sur le port ${PORT}`);
});
