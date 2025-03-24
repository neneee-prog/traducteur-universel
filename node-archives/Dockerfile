FROM node:16-bullseye

# Configuration réseau pour contourner les blocages
RUN echo "Acquire::http::Timeout \"60\";" > /etc/apt/apt.conf.d/99timeout && \
    echo "Acquire::https::Timeout \"60\";" >> /etc/apt/apt.conf.d/99timeout && \
    echo "deb http://deb.debian.org/debian bullseye main" > /etc/apt/sources.list && \
    echo "deb http://deb.debian.org/debian-security bullseye-security main" >> /etc/apt/sources.list && \
    echo "deb http://deb.debian.org/debian bullseye-updates main" >> /etc/apt/sources.list

# Installez les dépendances système CRITIQUES
RUN apt-get update -o Acquire::Retries=5 && apt-get install -y --fix-missing \
    python3.9 \
    python3-pip \
    make \
    g++ \
    libffi-dev \
    portaudio19-dev \
    ca-certificates

# Configurez Python
ENV PYTHON=/usr/bin/python3.9

WORKDIR /app

# Copiez les dépendances Node.js et installez-les
COPY package*.json ./
RUN npm install --python=/usr/bin/python3.9 --force

# Copiez le code Python
COPY traducteur-audio/ ./traducteur-audio

# Installez les dépendances Python
RUN pip3 install --index-url=https://pypi.org/simple -r traducteur-audio/requirements.txt --no-cache-dir

# Copiez le reste du code
COPY . .

EXPOSE 3000
CMD ["node", "src/server.js"]
