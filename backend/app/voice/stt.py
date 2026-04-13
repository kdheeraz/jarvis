from loguru import logger

_stt_model = None


def get_stt_model():
    """Get or create the STT model singleton."""
    global _stt_model
    if _stt_model is not None:
        return _stt_model

    from fastrtc import get_stt_model as get_whisper_stt
    _stt_model = get_whisper_stt()
    logger.info("STT model loaded (distil-whisper)")
    return _stt_model
