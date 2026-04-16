from loguru import logger

_stt_model = None


def get_stt_model():
    """Get or create the STT model singleton."""
    global _stt_model
    if _stt_model is not None:
        return _stt_model

    from distil_whisper_fastrtc import get_stt_model
    _stt_model = get_stt_model()
    logger.info("STT model loaded (distil-whisper)")
    return _stt_model
