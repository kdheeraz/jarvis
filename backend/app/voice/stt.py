from loguru import logger

from app.config import get_config

_stt_model = None


def get_stt_model():
    """Get or create the STT model singleton."""
    global _stt_model
    if _stt_model is not None:
        return _stt_model

    config = get_config()
    name = config.voice.stt_model

    if name in ("faster-whisper", "faster_whisper"):
        from app.voice.stt_faster_whisper import FasterWhisperSTT

        fw = config.voice.faster_whisper
        _stt_model = FasterWhisperSTT(
            model_size=fw.model_size,
            device=fw.device,
            compute_type=fw.compute_type,
            beam_size=fw.beam_size,
            vad_filter=fw.vad_filter,
            language=fw.language,
        )
    elif name == "distil-whisper":
        from distil_whisper_fastrtc import get_stt_model as _get

        _stt_model = _get()
        logger.info("STT model loaded (distil-whisper)")
    else:
        raise ValueError(f"Unknown STT model: {name}")

    return _stt_model
