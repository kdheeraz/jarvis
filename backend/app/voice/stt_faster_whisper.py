from typing import Tuple

import numpy as np
from loguru import logger


class FasterWhisperSTT:
    """CTranslate2-based Whisper — faster and lighter than HF distil-whisper.

    Matches the `stt(audio)` interface fastrtc expects:
        audio: (sample_rate, np.ndarray[int16|float32])
    """

    TARGET_SR = 16000

    def __init__(
        self,
        model_size: str = "small.en",
        device: str = "cpu",
        compute_type: str = "int8",
        beam_size: int = 1,
        vad_filter: bool = False,
        language: str | None = "en",
    ):
        from faster_whisper import WhisperModel

        self.model = WhisperModel(
            model_size, device=device, compute_type=compute_type
        )
        self.beam_size = beam_size
        self.vad_filter = vad_filter
        self.language = language
        logger.info(
            f"faster-whisper loaded: model={model_size} device={device} "
            f"compute_type={compute_type}"
        )

    def stt(self, audio: Tuple[int, np.ndarray]) -> str:
        sample_rate, audio_np = audio

        # Flatten to 1-D mono
        if audio_np.ndim > 1:
            audio_np = audio_np.reshape(-1)

        # int16 → float32 in [-1, 1]
        if audio_np.dtype == np.int16:
            audio_np = audio_np.astype(np.float32) / 32768.0
        elif audio_np.dtype != np.float32:
            audio_np = audio_np.astype(np.float32)

        # Resample to 16 kHz (faster-whisper requires it)
        if sample_rate != self.TARGET_SR:
            try:
                import librosa

                audio_np = librosa.resample(
                    audio_np, orig_sr=sample_rate, target_sr=self.TARGET_SR
                )
            except ImportError:
                # Fallback: naive linear resample. Accuracy will suffer but
                # better than crashing if librosa isn't installed.
                ratio = self.TARGET_SR / float(sample_rate)
                new_len = int(round(len(audio_np) * ratio))
                audio_np = np.interp(
                    np.linspace(0, len(audio_np) - 1, new_len),
                    np.arange(len(audio_np)),
                    audio_np,
                ).astype(np.float32)

        segments, _ = self.model.transcribe(
            audio_np,
            beam_size=self.beam_size,
            vad_filter=self.vad_filter,
            language=self.language,
            condition_on_previous_text=False,
        )
        return " ".join(seg.text for seg in segments).strip()
