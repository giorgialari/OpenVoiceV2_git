import os
import time
import torch
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import StreamingResponse
from typing import Optional
from melo.api import TTS
import tempfile

logging.basicConfig(level=logging.INFO)

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Device setup
device = "cuda:0" if torch.cuda.is_available() else "cpu"
output_dir = 'outputs'
os.makedirs(output_dir, exist_ok=True)

# Available base speakers
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

if device == "cpu":
    base_speakers = ['en-newest']

for accent in base_speakers:
    logging.info(f'Loading {accent}...')
    model[accent] = TTS(language=key_map[accent][1], device=device)
    logging.info('...done.')

logging.info('Loaded TTS models.')

def iterfile(file_path: str, chunk_size: int = 8192):
    """
    Legge il file in blocchi e, una volta terminata la lettura, elimina il file.
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

    if accent not in model:
        logging.info(f'Loading {accent}...')
        model[accent] = TTS(language=key_map[accent][1], device=device)
        logging.info('...done.')

    try:
        # Crea un file temporaneo che non viene eliminato automaticamente
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            tmp_filename = tmp_file.name

        # Genera l'audio e salvalo nel file temporaneo
        model[accent].tts_to_file(
            text, 
            model[accent].hps.data.spk2id[key_map[accent][0]], 
            tmp_filename, 
            speed=speed
        )

        # Restituisci la StreamingResponse usando il generatore "iterfile"
        return StreamingResponse(iterfile(tmp_filename), media_type="audio/wav")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
