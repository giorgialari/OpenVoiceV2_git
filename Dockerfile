# Usa Python come base (Railway supporta Python 3.9+)
FROM python:3.9

# Imposta la directory di lavoro
WORKDIR /app

# Copia tutto il codice nel container
COPY . /app/

# Assegna i permessi di esecuzione allo script
RUN chmod +x railway-build.sh

# Installa le dipendenze di sistema
RUN apt-get update && apt-get install -y ffmpeg libmagic-dev unzip wget

# Esegui lo script di installazione
RUN ./railway-build.sh

# Esponi la porta per l'API
ENV PORT=8000
EXPOSE $PORT

# Comando per avviare FastAPI con Uvicorn
CMD ["uvicorn", "openvoice.openvoice_server:app", "--host", "0.0.0.0", "--port", "8000"]