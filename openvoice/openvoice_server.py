import os
import torch
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import StreamingResponse
from typing import Optional
from melo.api import TTS
import tempfile
from threading import Lock
import traceback

logging.basicConfig(level=logging.INFO)

app = FastAPI()

# Abilita il CORS per tutte le origini
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup dispositivo
device = "cuda:0" if torch.cuda.is_available() else "cpu"
output_dir = 'outputs'
os.makedirs(output_dir, exist_ok=True)

# Definizione degli accenti disponibili e mappatura chiavi
base_speakers = ['en-au', 'en-br', 'en-default', 'en-india', 'en-newest', 'en-us', 'es', 'fr', 'jp', 'kr', 'zh']
key_map = {
    'en-newest': ('EN-Newest', 'EN_NEWEST'),
    'en-us': ('EN-US', 'EN'),
    'en-br': ('EN-BR', 'EN'),
    'en-india': ('EN_INDIA', 'EN'),
    'en-au': ('EN-AU', 'EN'),
    'en-default': ('EN-Default', 'EN'),
    'es': ('ES', 'ES'),
    'fr': ('FR', 'FR'),
    'jp': ('JP', 'JP'),
    'kr': ('KR', 'KR'),
    'zh': ('ZH', 'ZH')
}

logging.info('Loading TTS models...')
model = {}
# Lock per evitare accessi concorrenti al metodo tts_to_file
tts_lock = Lock()

# Se si usa la CPU, limitiamo gli accenti (per motivi di prestazioni)
if device == "cpu":
    base_speakers = ['en-newest']

# Carica il modello per ogni accento disponibile
for accent in base_speakers:
    logging.info(f'Loading {accent}...')
    model[accent] = TTS(language=key_map[accent][1], device=device)
    logging.info('...done.')

logging.info('Loaded TTS models.')

def iterfile(file_path: str, chunk_size: int = 8192):
    """
    Legge il file in blocchi e, al termine, lo elimina.
    """
    try:
        with open(file_path, "rb") as file:
            while True:
                chunk = file.read(chunk_size)
                if not chunk:
                    break
                yield chunk
    finally:
        try:
            os.remove(file_path)
        except Exception as e:
            logging.error(f"Errore durante l'eliminazione del file {file_path}: {e}")

@app.get("/base_tts/")
async def base_tts(text: str, accent: Optional[str] = 'en-newest', speed: Optional[float] = 1.0):
    global model

    # Se il modello per l'accento richiesto non è stato caricato, lo carica
    if accent not in model:
        logging.info(f'Loading {accent}...')
        model[accent] = TTS(language=key_map[accent][1], device=device)
        logging.info('...done.')

    try:
        # Crea un file temporaneo che salverà l'audio generato
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            tmp_filename = tmp_file.name

        # Usa un lock per evitare conflitti se ci sono richieste concorrenti
        with tts_lock:
            model[accent].tts_to_file(
                text, 
                model[accent].hps.data.spk2id[key_map[accent][0]], 
                tmp_filename, 
                speed=speed
            )

        # Ritorna il file audio come StreamingResponse
        return StreamingResponse(iterfile(tmp_filename), media_type="audio/wav")
    except Exception as e:
        logging.error("Errore nella generazione TTS: " + str(e))
        logging.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
