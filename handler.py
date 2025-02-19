import os
import tempfile
import base64
import torch
import logging
from melo.api import TTS

logging.basicConfig(level=logging.INFO)

# Dizionario per mappare l'accento ai parametri necessari (nome e codice)
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

device = "cuda:0" if torch.cuda.is_available() else "cpu"
models = {}  # Qui salveremo i modelli per ogni accento

def load_model(accent: str):
    """
    Carica il modello per l'accento specificato se non è già stato caricato.
    """
    global models
    if accent not in key_map:
        raise ValueError(f"Accento '{accent}' non supportato.")
        
    if accent not in models:
        try:
            models[accent] = TTS(language=key_map[accent][1], device=device)
            logging.info(f"Modello per l'accento '{accent}' caricato correttamente.")
        except Exception as e:
            logging.error(f"Errore durante il caricamento del modello per l'accento '{accent}': {e}")
            raise e
    return models[accent]

def init():
    """
    Funzione di inizializzazione: carica il modello di default (qui 'en-newest').
    """
    load_model("en-newest")
    logging.info("Inizializzazione completata.")

def run(payload):
    """
    Funzione di inferenza:
    - payload: dizionario che deve contenere almeno il campo "text".
      Può opzionalmente contenere "accent" (default 'en-newest') e "speed" (default 1.0).
    La funzione restituisce un dizionario con la chiave "audio" contenente l'audio in base64.
    """
    text = payload.get("text", "")
    accent = payload.get("accent", "en-newest")
    speed = payload.get("speed", 1.0)

    if not text:
        return {"error": "Nessun testo fornito."}

    try:
        # Carica il modello per l'accento richiesto (o usa quello già caricato)
        model = load_model(accent)
    except Exception as e:
        return {"error": f"Errore nel caricamento del modello per l'accento '{accent}': {str(e)}"}

    # Creazione di un file temporaneo per salvare l'audio
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
        tmp_filename = tmp_file.name

    try:
        # Genera l'audio e lo salva nel file temporaneo
        model.tts_to_file(
            text,
            model.hps.data.spk2id[key_map[accent][0]],
            tmp_filename,
            speed=speed
        )

        # Legge il file audio generato
        with open(tmp_filename, "rb") as f:
            audio_bytes = f.read()

        # Codifica l'audio in base64 per poterlo restituire in JSON
        audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
        return {"audio": audio_base64}
    except Exception as e:
        logging.error(f"Errore durante l'inferenza: {e}")
        return {"error": str(e)}
    finally:
        try:
            os.remove(tmp_filename)
        except Exception as e:
            logging.error(f"Errore durante l'eliminazione del file temporaneo {tmp_filename}: {e}")
