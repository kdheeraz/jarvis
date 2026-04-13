from typing import Generator

import numpy as np
from loguru import logger

from app.config import get_config


class PiperTTSModel:
    """Piper TTS wrapper that yields FastRTC-compatible audio tuples."""

    def __init__(self, model_path: str, config_path: str):
        from piper.voice import PiperVoice

        self.voice = PiperVoice.load(model_path, config_path)
        self.sample_rate = self.voice.config.sample_rate
        logger.info(f"Piper TTS loaded: {model_path} (sample_rate={self.sample_rate})")

    def stream_tts_sync(self, text: str) -> Generator:
        """Synthesize text and yield (sample_rate, audio_array) tuples."""
        for chunk_obj in self.voice.synthesize(text):
            audio_bytes = chunk_obj.audio_int16_bytes
            audio_1d = np.frombuffer(audio_bytes, dtype=np.int16)
            audio_2d = audio_1d.reshape(1, -1)
            yield (self.sample_rate, audio_2d)


_tts_model = None


def get_tts_model():
    """Get or create the TTS model singleton."""
    global _tts_model
    if _tts_model is not None:
        return _tts_model

    config = get_config()

    if config.voice.tts_model == "piper":
        _tts_model = PiperTTSModel(
            model_path=config.voice.piper.model_path,
            config_path=config.voice.piper.config_path,
        )
    elif config.voice.tts_model == "kokoro":
        from fastrtc import get_tts_model as get_kokoro_tts
        _tts_model = get_kokoro_tts()
    else:
        raise ValueError(f"Unknown TTS model: {config.voice.tts_model}")

    return _tts_model
