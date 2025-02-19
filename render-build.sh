#!/bin/bash

# Aggiorna il sistema e installa dipendenze di sistema necessarie
apt-get update && apt-get install -y ffmpeg libmagic-dev unzip wget

# Aggiorna pip e installa setuptools e wheel per evitare errori
pip install --upgrade pip
pip install --upgrade setuptools wheel

# Installa manualmente melotts prima dei requirements.txt per evitare errori
pip install git+https://github.com/myshell-ai/MeloTTS.git
python -m unidic download

# Installa tutte le dipendenze
pip install -r requirements.txt


# Scarica il file ZIP dei checkpoints
echo "Scaricamento dei checkpoints..."
wget -O checkpoints.zip "https://myshell-public-repo-host.s3.amazonaws.com/openvoice/checkpoints_v2_0417.zip"

# Estrai il file ZIP nella root del progetto
echo "Estrazione dei checkpoints..."
unzip -o checkpoints.zip -d ./

# Rimuovi il file ZIP per risparmiare spazio
rm checkpoints.zip