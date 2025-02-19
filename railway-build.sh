#!/bin/bash

set -e  # Termina lo script se un comando fallisce

echo "🔧 Aggiornamento del sistema e installazione delle dipendenze..."
apt-get update && apt-get install -y ffmpeg libmagic-dev unzip wget

echo "🚀 Aggiornamento di pip, setuptools e wheel..."
pip install --upgrade pip setuptools wheel

echo "🎙️ Installazione di MeloTTS..."
pip install git+https://github.com/myshell-ai/MeloTTS.git
python -m unidic download

echo "📦 Installazione delle dipendenze..."
pip install -r requirements.txt

echo "📥 Scaricamento dei checkpoints..."
wget -O checkpoints.zip "https://myshell-public-repo-host.s3.amazonaws.com/openvoice/checkpoints_v2_0417.zip"

echo "📂 Estrazione dei checkpoints..."
unzip -o checkpoints.zip -d ./

echo "🗑️ Pulizia dei file temporanei..."
rm checkpoints.zip

echo "✅ Installazione completata con successo!"