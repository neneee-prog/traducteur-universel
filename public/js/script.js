document.addEventListener('DOMContentLoaded', () => {
  const body = document.body;
  let currentFontSize = parseFloat(window.getComputedStyle(body).fontSize);

  // Modes (nuit, daltonien, focus, etc.)
  document.getElementById('nightMode')?.addEventListener('click', () => {
    body.classList.toggle('night-mode');
    updateThemeVariables();
  });
  document.getElementById('daltonianMode')?.addEventListener('click', () => {
    body.classList.toggle('daltonian-mode');
  });
  document.getElementById('focusMode')?.addEventListener('click', () => {
    body.classList.toggle('focus-mode');
    document.querySelectorAll('.sidebar, .right-sidebar').forEach(sidebar => {
      sidebar.style.transform = body.classList.contains('focus-mode')
        ? 'translateX(-300px)'
        : 'none';
    });
  });

  // Ajustement de la taille de police
  document.getElementById('fontSizeUp')?.addEventListener('click', () => {
    currentFontSize += 2;
    body.style.fontSize = `${currentFontSize}px`;
  });
  document.getElementById('fontSizeDown')?.addEventListener('click', () => {
    currentFontSize = Math.max(10, currentFontSize - 2);
    body.style.fontSize = `${currentFontSize}px`;
  });

  // Création d'un nouveau cours
  window.addCourse = async () => {
    const courseName = prompt("Entrez le nom du nouveau cours :");
    if (courseName) {
      try {
        const res = await fetch('/api/courses', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name: courseName })
        });
        const newCourse = await res.json();
        window.location.href = `course.html?id=${newCourse.id}`;
      } catch (error) {
        console.error("Erreur lors de la création du cours :", error);
      }
    }
  };

  // ----- Gestion du TTS (Web Speech API) -----
  let ttsQueue = [];
  let isReading = false;

  // Fonction pour découper le texte en segments courts (~200 caractères)
  function splitTextIntoChunks(text, maxLength = 200) {
    let parts = text.split(/([.?!]+)/);
    let phrases = [];
    for (let i = 0; i < parts.length; i += 2) {
      let sentence = (parts[i] || "").trim();
      let punct = (parts[i+1] || "").trim();
      if (sentence) {
        phrases.push(sentence + (punct ? punct : ""));
      }
    }
    let finalChunks = [];
    phrases.forEach(ph => {
      if (ph.length <= maxLength) {
        finalChunks.push(ph.trim());
      } else {
        let start = 0;
        while (start < ph.length) {
          let sub = ph.substring(start, start + maxLength);
          finalChunks.push(sub.trim());
          start += maxLength;
        }
      }
    });
    return finalChunks.filter(c => c.length > 0);
  }

  // Ajoute un segment à la file TTS et lance la lecture si nécessaire
  function enqueueText(text) {
    if (text && text.trim()) {
      ttsQueue.push(text.trim());
    }
    if (!isReading) {
      speakNext();
    }
  }

  // Lit le prochain segment de la file TTS
  function speakNext() {
    if (ttsQueue.length === 0) {
      isReading = false;
      return;
    }
    isReading = true;
    const text = ttsQueue.shift();
    if (!text) {
      isReading = false;
      return;
    }
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = "fr-FR";
    utterance.rate = 0.9;
    utterance.pitch = 1.0;
    const voices = window.speechSynthesis.getVoices();
    let chosenVoice = voices.find(v => v.name.includes("Google") && v.lang === 'fr-FR');
    if (!chosenVoice) {
      chosenVoice = voices.find(v => v.lang === 'fr-FR');
    }
    if (chosenVoice) {
      utterance.voice = chosenVoice;
    }
    utterance.onend = () => {
      isReading = false;
      speakNext();
    };
    utterance.onerror = (err) => {
      console.error("TTS error:", err);
      isReading = false;
      speakNext();
    };
    window.speechSynthesis.speak(utterance);
  }

  // Arrête la lecture TTS et vide la file
  function stopTTS() {
    ttsQueue = [];
    window.speechSynthesis.cancel();
    isReading = false;
  }

  document.getElementById('stopTTSBtn')?.addEventListener('click', () => {
    stopTTS();
  });

  // ----- Connexion WebSocket pour la traduction en temps réel -----
  const translatedTextElement = document.getElementById('transcriptionOutput');
  const ws = new WebSocket('ws://localhost:8081/api/realtime/ws');

  ws.onopen = () => {
    console.log('Connexion WebSocket établie');
  };

  ws.onmessage = (event) => {
    console.log('Message reçu via WebSocket:', event.data);
    const chunks = splitTextIntoChunks(event.data, 200);
    chunks.forEach(chunk => {
      if (chunk.split(' ').length < 3) {
        console.log("Chunk trop court =>", chunk);
        return;
      }
      const lineEl = document.createElement('div');
      lineEl.classList.add('translated-line');
      lineEl.textContent = chunk;
      translatedTextElement.appendChild(lineEl);
      translatedTextElement.scrollTop = translatedTextElement.scrollHeight;
      enqueueText(chunk);
    });
  };

  ws.onerror = (error) => {
    console.error('Erreur WebSocket:', error);
  };

  ws.onclose = () => {
    console.log('Connexion WebSocket fermée');
  };

  // ----- Bouton Micro -----
  let mediaRecorder;
  const startStopBtn = document.getElementById('startStopBtn');
  let isRecording = false;

  startStopBtn?.addEventListener('click', async () => {
    if (!isRecording) {
      // Envoyer "start" pour déclencher l'enregistrement côté serveur
      ws.send("start");
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        mediaRecorder.ondataavailable = async (e) => {
          if (e.data.size) {
            console.log("Données audio disponibles (traitement côté serveur via WebSocket).");
          }
        };
        mediaRecorder.start(100);
        startStopBtn.innerHTML = '<i class="fas fa-stop fa-2x"></i>';
        isRecording = true;
      } catch (error) {
        alert("Microphone inaccessible");
      }
    } else {
      // Envoyer "stop" pour arrêter l'enregistrement côté serveur
      ws.send("stop");
      if (mediaRecorder) {
        mediaRecorder.stop();
        mediaRecorder = null;
      }
      startStopBtn.innerHTML = '<i class="fas fa-microphone fa-2x"></i>';
      isRecording = false;
      stopTTS(); // Arrêter toute lecture en cours
    }
  });

  // ----- Gestion des fichiers (upload + traduction) -----
  window.uploadedFiles = {};

  function addTranslationFile(file) {
    window.uploadedFiles[file.name] = file;
    const fileItem = document.createElement('div');
    fileItem.className = 'translation-file-item';
    fileItem.innerHTML = `
      <div>${file.name}</div>
      <div class="translation-actions">
        <i class="fas fa-play" onclick="translateFileHandler('${file.name}')"></i>
        <i class="fas fa-download" onclick="downloadFile('${file.name}')"></i>
      </div>
    `;
    const translationFiles = document.getElementById('translationFiles');
    if (translationFiles) {
      translationFiles.appendChild(fileItem);
    }
  }

  document.getElementById('fileInput')?.addEventListener('change', (e) => {
    Array.from(e.target.files).forEach(file => addTranslationFile(file));
  });
  document.querySelector('.upload-box')?.addEventListener('drop', (e) => {
    e.preventDefault();
    Array.from(e.dataTransfer.files).forEach(file => addTranslationFile(file));
  });
  document.querySelector('.upload-box')?.addEventListener('dragover', e => e.preventDefault());

  window.translateFileHandler = (fileName) => {
    const fileObj = window.uploadedFiles[fileName];
    if (fileObj) {
      translateFile(fileObj);
    } else {
      console.error("Fichier non trouvé :", fileName);
    }
  };

  window.translateFile = async (fileObj) => {
    try {
      const formData = new FormData();
      formData.append("file", fileObj);
      const response = await fetch(`/api/files/translateFile`, {
        method: 'POST',
        body: formData
      });
      if (!response.ok) {
        throw new Error("Erreur serveur: " + response.status);
      }
      const data = await response.json();
      translatedTextElement.textContent = data.translatedText || "Traduction non disponible";
    } catch (error) {
      console.error('Erreur lors de la traduction du fichier:', error);
    }
  };

  window.downloadFile = async (fileName) => {
    try {
      const response = await fetch(`/api/files/downloadFile?filename=${encodeURIComponent(fileName)}`);
      if (!response.ok) {
        throw new Error("Erreur serveur: " + response.status);
      }
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = fileName;
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (error) {
      console.error('Erreur lors du téléchargement du fichier:', error);
    }
  };

  // ----- Bouton de sauvegarde de la traduction -----
  document.getElementById('saveBtn')?.addEventListener('click', async () => {
    try {
      const text = translatedTextElement?.textContent || "";
      await fetch('/api/translations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text })
      });
      alert('Traduction sauvegardée !');
    } catch (e) {
      console.error(e);
    }
  });

  loadCourses();

  async function loadCourses() {
    try {
      const res = await fetch('/api/courses');
      const courses = await res.json();
      const container = document.getElementById('courses');
      if (container) {
        container.innerHTML = courses.map(course => `
          <a href="course.html?id=${course.id}" class="course-item-link">
            <div class="course-item" data-id="${course.id}">
              ${course.name}
              <i class="fas fa-ellipsis-v" onclick="event.preventDefault(); showCourseMenu(event, ${course.id})"></i>
            </div>
          </a>
        `).join('');
      }
    } catch (error) {
      console.error('Erreur chargement des cours:', error);
    }
  }

  function showCourseMenu(event, courseId) {
    event.stopPropagation();
    const menu = document.createElement('div');
    menu.className = 'course-context-menu';
    menu.style.position = 'absolute';
    menu.style.left = `${event.pageX}px`;
    menu.style.top = `${event.pageY}px`;
    menu.innerHTML = `
      <div onclick="renameCourse(${courseId})"><i class="fas fa-pencil-alt"></i> Renommer</div>
      <div onclick="deleteCourse(${courseId})"><i class="fas fa-trash"></i> Supprimer</div>
    `;
    document.body.appendChild(menu);
    document.addEventListener('click', () => { menu.remove(); }, { once: true });
  }

  window.renameCourse = async (id) => {
    const newName = prompt("Nouveau nom :");
    if (newName) {
      try {
        await fetch(`/api/courses/${id}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name: newName })
        });
        loadCourses();
      } catch (e) {
        console.error(e);
      }
    }
  };

  window.deleteCourse = async (id) => {
    if (confirm('Confirmer la suppression ?')) {
      try {
        await fetch(`/api/courses/${id}`, { method: 'DELETE' });
        loadCourses();
      } catch (e) {
        console.error(e);
      }
    }
  };
});

// Fonction de mise à jour des variables CSS pour le mode nuit
function updateThemeVariables() {
  const isNight = document.body.classList.contains('night-mode');
  document.documentElement.style.setProperty('--glass-bg', isNight ? 'rgba(30,30,30,0.9)' : 'rgba(255,255,255,0.9)');
  document.documentElement.style.setProperty('--glass-fg', isNight ? '#ffffff' : '#000000');
}
  

   

   