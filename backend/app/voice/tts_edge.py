import asyncio
import concurrent.futures
import io
from typing import Generator

import numpy as np
from loguru import logger


class EdgeTTSModel:
    """Microsoft Edge TTS (Azure neural voices) via the unofficial `edge-tts` library.

    Free, no API key. Synthesis runs on Microsoft's servers, so local CPU stays
    free — which is the whole point of using it over Piper on small boxes.
    """

    def __init__(
        self,
        voice: str = "en-US-AriaNeural",
        rate: str = "+0%",
        pitch: str = "+0Hz",
        sample_rate: int = 24000,
    ):
        self.voice = voice
        self.rate = rate
        self.pitch = pitch
        self.sample_rate = sample_rate
        self._pool = concurrent.futures.ThreadPoolExecutor(max_workers=2)
        logger.info(f"Edge TTS ready: voice={voice}")

    def stream_tts_sync(self, text: str) -> Generator:
        if not text or not text.strip():
            return

        # edge-tts is async; run it on a dedicated thread so we never clash with
        # a running event loop in the caller's context.
        future = self._pool.submit(self._run_synth, text)
        audio_1d = future.result()

        if audio_1d.size == 0:
            return

        # Yield the whole utterance in one piece. Splitting pre-decoded PCM into
        # small fixed windows introduces tiny gaps at chunk boundaries in
        # fastrtc's jitter buffer, which show up as intra-word stutter.
        yield (self.sample_rate, audio_1d.reshape(1, -1))

    def _run_synth(self, text: str) -> np.ndarray:
        return asyncio.run(self._synthesize_to_pcm(text))

    async def _synthesize_to_pcm(self, text: str) -> np.ndarray:
        import edge_tts

        communicate = edge_tts.Communicate(
            text, self.voice, rate=self.rate, pitch=self.pitch
        )
        mp3_buffer = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk.get("type") == "audio":
                mp3_buffer.write(chunk["data"])

        if mp3_buffer.getbuffer().nbytes == 0:
            logger.warning("[edge-tts] empty audio response")
            return np.array([], dtype=np.int16)

        mp3_buffer.seek(0)
        return self._decode_mp3_to_pcm(mp3_buffer)

    def _decode_mp3_to_pcm(self, buf: io.BytesIO) -> np.ndarray:
        """MP3 bytes → int16 mono PCM at self.sample_rate via PyAV (bundled with aiortc)."""
        import av

        container = av.open(buf, format="mp3")
        try:
            stream = container.streams.audio[0]
            resampler = av.AudioResampler(
                format="s16", layout="mono", rate=self.sample_rate
            )
            pcm_chunks: list[np.ndarray] = []

            def _collect(frames):
                # PyAV's resampler returns a list in newer versions, a single
                # frame in older ones. Normalize.
                if frames is None:
                    return
                if not isinstance(frames, list):
                    frames = [frames]
                for f in frames:
                    if f is None:
                        continue
                    arr = f.to_ndarray()
                    if arr.ndim > 1:
                        arr = arr.reshape(-1)
                    pcm_chunks.append(arr.astype(np.int16, copy=False))

            for frame in container.decode(stream):
                _collect(resampler.resample(frame))
            _collect(resampler.resample(None))  # flush

            if not pcm_chunks:
                return np.array([], dtype=np.int16)
            return np.concatenate(pcm_chunks)
        finally:
            container.close()
