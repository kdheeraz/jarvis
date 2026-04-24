import io
import os
import wave
from typing import Generator

import httpx
import numpy as np
from loguru import logger


class GroqTTSModel:
    """Groq PlayAI TTS — natural-sounding cloud voices on the Groq free tier.

    Matches the `stream_tts_sync(text)` interface (same as Piper/Edge/Kokoro).
    One HTTP call per invocation; full WAV buffered, then yielded.
    """

    def __init__(
        self,
        voice: str = "Calum-PlayAI",
        model: str = "playai-tts",
        base_url: str = "https://api.groq.com/openai/v1",
        api_key_env: str = "GROQ_API_KEY",
        timeout: float = 30.0,
    ):
        self.voice = voice
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.api_key = os.environ.get(api_key_env, "").strip()
        self.timeout = timeout
        if not self.api_key:
            raise RuntimeError(
                f"Groq TTS requires env var {api_key_env}. Add it to .env."
            )
        self._client = httpx.Client(timeout=self.timeout)
        # Groq PlayAI returns 48 kHz mono PCM inside a WAV container. Default
        # here is a safe fallback; the real rate is read from each response.
        self.sample_rate = 48000
        logger.info(f"Groq TTS ready: voice={voice} model={model}")

    def stream_tts_sync(self, text: str) -> Generator:
        if not text or not text.strip():
            return

        try:
            wav_bytes = self._synthesize(text)
        except httpx.HTTPStatusError as e:
            logger.warning(f"[groq-tts] HTTP {e.response.status_code}: {e.response.text[:200]}")
            return
        except Exception as e:
            logger.warning(f"[groq-tts] synthesis failed: {e}")
            return

        if not wav_bytes:
            return

        sr, audio = self._decode_wav(wav_bytes)
        if audio.size == 0:
            return
        yield (sr, audio.reshape(1, -1))

    def _synthesize(self, text: str) -> bytes:
        resp = self._client.post(
            f"{self.base_url}/audio/speech",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "voice": self.voice,
                "input": text,
                "response_format": "wav",
            },
        )
        resp.raise_for_status()
        return resp.content

    def _decode_wav(self, data: bytes) -> tuple[int, np.ndarray]:
        with wave.open(io.BytesIO(data), "rb") as wf:
            sr = wf.getframerate()
            n_channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            frames = wf.readframes(wf.getnframes())

        if sampwidth == 2:
            audio = np.frombuffer(frames, dtype=np.int16)
        elif sampwidth == 1:
            audio = (np.frombuffer(frames, dtype=np.uint8).astype(np.int16) - 128) << 8
        else:
            raise ValueError(f"Unsupported WAV sample width: {sampwidth}")

        if n_channels > 1:
            audio = audio.reshape(-1, n_channels).mean(axis=1).astype(np.int16)
        return sr, audio
