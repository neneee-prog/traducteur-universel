document.addEventListener('DOMContentLoaded', () => {
    const socket = io();
    const body = document.body;
    let currentFontSize = parseFloat(window.getComputedStyle(body).fontSize);
    const transcriptionOutput = document.getElementById('transcriptionOutput');

    document.getElementById('nightMode')?.addEventListener('click', () => {
        body.classList.toggle('night-mode');
        updateThemeVariables();
    });
    document.getElementById('focusMode')?.addEventListener('click', () => {
        body.classList.toggle('focus-mode');
        const sidebar = document.querySelector('.sidebar');
        if(sidebar) sidebar.style.transform = body.classList.contains('focus-mode') ? 'translateX(-300px)' : 'none';
    });
    document.getElementById('fontSizeUp')?.addEventListener('click', () => {
        currentFontSize += 2;
        body.style.fontSize = `${currentFontSize}px`;
    });
    document.getElementById('fontSizeDown')?.addEventListener('click', () => {
        currentFontSize = Math.max(10, currentFontSize - 2);
        body.style.fontSize = `${currentFontSize}px`;
    });
    document.getElementById('daltonianMode')?.addEventListener('click', () => {
        body.classList.toggle('daltonian-mode');
    });

    let mediaRecorder;
    const startStopBtn = document.getElementById('startStopBtn');
    startStopBtn.addEventListener('click', async () => {
        if(!mediaRecorder) {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                mediaRecorder = new MediaRecorder(stream);
                mediaRecorder.ondataavailable = e => {
                    if(e.data.size) socket.emit('audio_data', e.data);
                };
                mediaRecorder.start(100);
                startStopBtn.innerHTML = '<i class="fas fa-stop fa-2x"></i>';
                socket.emit('start_recording');
            } catch {
                alert("Microphone non accessible");
            }
        } else {
            mediaRecorder.stop();
            mediaRecorder = null;
            startStopBtn.innerHTML = '<i class="fas fa-microphone fa-2x"></i>';
            socket.emit('stop_recording');
        }
    });

    socket.on('translation', data => {
        transcriptionOutput.textContent = data.translatedText;
        transcriptionOutput.style.animation = 'fadeIn 0.5s';
        speechSynthesis.speak(new SpeechSynthesisUtterance(data.translatedText));
    });

    document.getElementById('saveBtn')?.addEventListener('click', async () => {
        const text = transcriptionOutput.textContent;
        try {
            const res = await fetch('/submit-translation', {
                method:'POST',
                headers:{'Content-Type':'application/json'},
                body:JSON.stringify({ text })
            });
            if(res.ok) alert('Traduction sauvegardée !');
        } catch(e) {
            console.error(e);
        }
    });

    async function loadCourses() {
        const res = await fetch('/api/courses');
        const courses = await res.json();
        document.getElementById('courses').innerHTML = courses.map(c => `
            <div class="course-item" data-id="${c.id}">
                ${c.name}<i class="fas fa-chevron-right"></i>
            </div>`).join('');
    }

    document.querySelector('.sidebar-bar').onclick = async () => {
        const name = prompt("Nom du cours ?");
        if(name) {
            await fetch('/api/courses', {
                method:'POST',
                headers:{'Content-Type':'application/json'},
                body:JSON.stringify({ name })
            });
            loadCourses();
        }
    };

    window.addEventListener('resize', () => {
        const tw = document.querySelector('.transcription-window');
        if(tw) tw.style.left = window.innerWidth < 768 ? '50%' : '55%';
    });

    loadCourses();
});

function updateThemeVariables() {
    const isNight = document.body.classList.contains('night-mode');
    document.documentElement.style.setProperty('--glass-bg', isNight ? 'rgba(30,30,30,0.9)' : 'rgba(255,255,255,0.9)');
    document.documentElement.style.setProperty('--glass-fg', isNight ? '#fff' : '#000');
}
