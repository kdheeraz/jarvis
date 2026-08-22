from typing import Generator

import numpy as np
from loguru import logger

from app.config import get_config


class PiperTTSModel:
    """Piper TTS wrapper that yields FastRTC-compatible audio tuples."""

    # Piper emits one array per sentence, which can be several seconds of audio.
    # fastrtc can only act on a barge-in at a yield point — that is where it
    # raises GeneratorExit and drains the output queue — so handing it one huge
    # array means seconds of speech keep playing after you interrupt, and audio
    # already computed can land in the queue just after it was cleared. Slicing
    # the array caps that overrun at one slice.
    SLICE_MS = 40

    def __init__(self, model_path: str, config_path: str):
        from piper.voice import PiperVoice

        self.voice = PiperVoice.load(model_path, config_path)
        self.sample_rate = self.voice.config.sample_rate
        self._slice_samples = max(1, int(self.sample_rate * self.SLICE_MS / 1000))
        logger.info(f"Piper TTS loaded: {model_path} (sample_rate={self.sample_rate})")

    def stream_tts_sync(self, text: str) -> Generator:
        """Synthesize text and yield (sample_rate, audio_array) tuples."""
        for chunk_obj in self.voice.synthesize(text):
            audio_bytes = chunk_obj.audio_int16_bytes
            audio_1d = np.frombuffer(audio_bytes, dtype=np.int16)
            for start in range(0, audio_1d.size, self._slice_samples):
                audio_2d = audio_1d[start : start + self._slice_samples].reshape(1, -1)
                yield (self.sample_rate, audio_2d)


_tts_model = None


def reset_tts_model():
    """Clear the cached TTS singleton so the next get_tts_model() rebuilds it
    from current config. Call after a voice config change (engine, voice, speed).

    The rebuild is pre-warmed on a background thread so the next utterance does
    not eat the model's cold-load cost (Kokoro ~30s) as dead silence. Best-effort
    — if warming fails, get_tts_model() will simply rebuild on demand."""
    global _tts_model
    _tts_model = None
    logger.info("TTS model singleton reset; pre-warming new model in background")

    import threading

    def _warm():
        try:
            get_tts_model()
        except Exception as e:
            logger.warning(f"TTS pre-warm after reset failed: {e}")

    threading.Thread(target=_warm, daemon=True).start()


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
