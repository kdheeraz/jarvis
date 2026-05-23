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

    if config.voice.tts_model == "groq":
        from app.voice.tts_groq import GroqTTSModel

        _tts_model = GroqTTSModel(
            voice=config.voice.groq.voice,
            model=config.voice.groq.model,
            base_url=config.voice.groq.base_url,
            api_key_env=config.voice.groq.api_key_env,
        )
    elif config.voice.tts_model == "edge":
        from app.voice.tts_edge import EdgeTTSModel

        _tts_model = EdgeTTSModel(
            voice=config.voice.edge.voice,
            rate=config.voice.edge.rate,
            pitch=config.voice.edge.pitch,
        )
    elif config.voice.tts_model == "piper":
        _tts_model = PiperTTSModel(
            model_path=config.voice.piper.model_path,
            config_path=config.voice.piper.config_path,
        )
    elif config.voice.tts_model == "chattts":
        from app.voice.tts_chattts import ChatTTSModel

        c = config.voice.chattts
        _tts_model = ChatTTSModel(
            device=c.device,
            compile=c.compile,
            speaker_seed=c.speaker_seed,
            temperature=c.temperature,
            top_p=c.top_p,
            top_k=c.top_k,
            sample_rate=c.sample_rate,
            refine_text_prompt=c.refine_text_prompt,
        )
    elif config.voice.tts_model == "kokoro":
        from fastrtc import KokoroTTSOptions, get_tts_model as get_kokoro_tts

        base = get_kokoro_tts()
        options = KokoroTTSOptions(
            voice=config.voice.kokoro.voice,
            speed=config.voice.kokoro.speed,
            lang=config.voice.kokoro.lang,
        )

        class _KokoroWrapped:
            """Bind voice/speed/lang so the caller's stream_tts_sync(text) works."""

            def __init__(self, model, opts):
                self._model = model
                self._options = opts

            def stream_tts_sync(self, text):
                yield from self._model.stream_tts_sync(text, self._options)

        _tts_model = _KokoroWrapped(base, options)
        logger.info(
            f"Kokoro TTS loaded: voice={options.voice} speed={options.speed}"
        )
    else:
        raise ValueError(f"Unknown TTS model: {config.voice.tts_model}")

    return _tts_model
