import time
import threading
from pathlib import Path
from faster_whisper import WhisperModel

SUPPORTED_MODELS = {"tiny", "small", "medium", "large"}
DEFAULT_MODEL = "small"
IDLE_TTL = 300 

_models: dict[str, dict] = {}
_lock = threading.Lock()


def _cleanup_idle_models():
    now = time.time()
    with _lock:
        idle = [name for name, entry in _models.items() if now - entry["last_used"] >= IDLE_TTL]
        for name in idle:
            del _models[name]


def _schedule_cleanup():
    _cleanup_idle_models()
    timer = threading.Timer(60, _schedule_cleanup)
    timer.daemon = True
    timer.start()


_schedule_cleanup()


def get_model(model_name: str = DEFAULT_MODEL):
    if model_name not in SUPPORTED_MODELS:
        raise ValueError(f"Unsupported model: {model_name}. Choose from {SUPPORTED_MODELS}")

    with _lock:
        if model_name in _models:
            _models[model_name]["last_used"] = time.time()
            return _models[model_name]["model"]

        model = WhisperModel(model_name, device="cpu", compute_type="int8")
        _models[model_name] = {"model": model, "last_used": time.time()}
        return model


def transcribe_file(audio_path: Path, model_name: str = DEFAULT_MODEL):
    model = get_model(model_name)

    segments, info = model.transcribe(str(audio_path), vad_filter=True)

    text_parts = []
    seg_list = []
    for s in segments:
        text_parts.append(s.text)
        seg_list.append({
            "start": float(s.start),
            "end": float(s.end),
            "text": s.text,
        })

    return {
        "language": info.language,
        "language_probability": float(info.language_probability),
        "text": "".join(text_parts).strip(),
        "segments": seg_list,
        "model": model_name,
    }