import os
import torch
import logging
import tempfile
import psutil
from functools import lru_cache
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import StreamingResponse
from typing import Optional
from melo.api import TTS

logging.basicConfig(level=logging.INFO)

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],  
)

# Forza sempre la CPU per ridurre il consumo di memoria
device = "cpu"

# Mappa accenti e modelli
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

# Funzione per monitorare il consumo di RAM
def print_memory_usage(tag=""):
    process = psutil.Process()
    mem_info = process.memory_info()
    logging.info(f"[{tag}] RAM usata: {mem_info.rss / 1024 / 1024:.2f} MB")

# Cache per mantenere solo 2 modelli in memoria contemporaneamente
@lru_cache(maxsize=2)
def get_tts_model(accent):
    logging.info(f"Caricamento modello {accent}...")
    model = TTS(language=key_map[accent][1], device=device)
    logging.info(f"{accent} caricato.")
    return model

# Funzione per leggere e rimuovere il file dopo l'uso
def iterfile(file_path: str, chunk_size: int = 8192):
    try:
        with open(file_path, "rb") as file:
            while chunk := file.read(chunk_size):
                yield chunk
    finally:
        try:
            os.remove(file_path)
        except Exception as e:
            logging.error(f"Errore eliminando il file {file_path}: {e}")

@app.get("/base_tts/")
async def base_tts(text: str, accent: Optional[str] = 'en-newest', speed: Optional[float] = 1.0):
    try:
        print_memory_usage("PRIMA della generazione audio")

        # Carica il modello (massimo 2 modelli in RAM contemporaneamente)
        model = get_tts_model(accent)

        # Crea un file temporaneo
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            tmp_filename = tmp_file.name

        # Genera l'audio e salva nel file
        model.tts_to_file(
            text, 
            model.hps.data.spk2id[key_map[accent][0]], 
            tmp_filename, 
            speed=speed
        )

        print_memory_usage("DOPO la generazione audio")

        # Pulisce la memoria GPU (se Torch la sta usando)
        torch.cuda.empty_cache()

        # Restituisce il file audio
        return StreamingResponse(iterfile(tmp_filename), media_type="audio/wav")

    except Exception as e:
        logging.error(f"Errore in base_tts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)