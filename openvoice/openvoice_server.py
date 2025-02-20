import os
import torch
import logging
import tempfile
import traceback
import asyncio
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import StreamingResponse
from typing import Optional
from melo.api import TTS

logging.basicConfig(level=logging.INFO)

app = FastAPI()

# Configurazione CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Impostazione dispositivo: GPU se disponibile, altrimenti CPU
device = "cuda:0" if torch.cuda.is_available() else "cpu"

# Definizione delle lingue di interesse
# Usando: en-newest (inglese), fr (francese), es (spagnolo)
base_speakers = ['en-newest', 'fr', 'es']
key_map = {
    'en-newest': ('EN-Newest', 'EN_NEWEST'),
    'fr': ('FR', 'FR'),
    'es': ('ES', 'ES')
}

logging.info("Loading TTS models...")
model = {}
# Se si usa la CPU, potresti voler caricare solo l’inglese per migliorare le performance
if device == "cpu":
    base_speakers = ['en-newest']

for accent in base_speakers:
    logging.info(f"Loading model for {accent}...")
    model[accent] = TTS(language=key_map[accent][1], device=device)
    logging.info("...done.")
logging.info("Loaded TTS models.")

# Executor per operazioni CPU-bound
executor = ThreadPoolExecutor(max_workers=4)

def iterfile(file_path: str, chunk_size: int = 8192):
    """
    Legge il file a blocchi e, al termine, elimina il file temporaneo.
    """
    try:
        with open(file_path, "rb") as f:
            while True:
                data = f.read(chunk_size)
                if not data:
                    break
                yield data
    finally:
        try:
            os.remove(file_path)
            logging.info(f"Temporary file {file_path} deleted.")
        except Exception as e:
            logging.error(f"Error deleting file {file_path}: {e}")

def run_tts(accent: str, text: str, speed: float, tmp_filename: str):
    """
    Funzione da eseguire in background per generare l'audio TTS.
    """
    model[accent].tts_to_file(
        text,
        model[accent].hps.data.spk2id[key_map[accent][0]],
        tmp_filename,
        speed=speed
    )

@app.get("/synthesize_speech/")
async def synthesize_speech(text: str, accent: Optional[str] = 'en-newest', speed: Optional[float] = 1.0):
    """
    Sintetizza il testo in voce usando il modello TTS corrispondente.
    Le lingue disponibili sono:
      - en-newest (inglese)
      - fr (francese)
      - es (spagnolo)
    """
    if accent not in model:
        logging.info(f"Loading model for {accent}...")
        model[accent] = TTS(language=key_map[accent][1], device=device)
        logging.info("...done.")

    try:
        # Crea un file temporaneo per salvare l'audio generato
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            tmp_filename = tmp_file.name
        logging.info(f"Temporary file created: {tmp_filename}")

        # Esegui la sintesi TTS in background per non bloccare l'event loop
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(executor, run_tts, accent, text, speed, tmp_filename)

        # Ritorna il file audio come StreamingResponse; il file verrà eliminato dopo la lettura
        return StreamingResponse(iterfile(tmp_filename), media_type="audio/wav")
    except Exception as e:
        logging.error("Error in TTS synthesis: " + str(e))
        logging.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
