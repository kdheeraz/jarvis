from typing import Any

from loguru import logger

from app.config import get_config

# Per-connection voice conversation mapping is handled by fastrtc's
# per-handler `set_args` — we keep a reference to the mounted Stream so
# the bind endpoint can push conversation_id into the right connection.
_voice_stream: Any | None = None


def get_voice_stream() -> Any | None:
    return _voice_stream


def _make_args_persistent(handler) -> None:
    """Patch a fastrtc ReplyOnPause handler so additional args survive utterances.

    fastrtc's `StreamHandlerBase.reset()` — called after every utterance via
    `ReplyOnPause.reset()` → `super().reset()` — clears `args_set`. Because our
    handler takes an extra `conversation_id` param, `_needs_additional_inputs`
    is True and the next utterance blocks forever in `wait_for_args_sync()`
    (no UI component is wired to re-push args). We override the handler's
    reset so that after fastrtc's cleanup the event is re-armed, keeping the
    already-bound args valid for every subsequent utterance.
    """
    if getattr(handler, "_jarvis_persistent_args", False):
        return
    orig_reset = handler.reset

    def persistent_reset(*args, **kwargs):
        orig_reset(*args, **kwargs)
        try:
            if getattr(handler, "latest_args", None):
                handler.args_set.set()
        except Exception:
            pass

    handler.reset = persistent_reset
    handler._jarvis_persistent_args = True


def bind_voice_conversation(webrtc_id: str, conversation_id: str) -> bool:
    """Attach a conversation_id to an active webrtc connection.

    Returns True if the connection existed and the binding was applied.
    """
    stream = _voice_stream
    if stream is None:
        return False
    try:
        connections = getattr(stream, "connections", {}) or {}
        handlers = getattr(stream, "handlers", {}) or {}
        if webrtc_id not in connections:
            return False
        stream.set_input(webrtc_id, conversation_id)
        handler = handlers.get(webrtc_id)
        if handler is not None:
            _make_args_persistent(handler)
            try:
                if getattr(handler, "latest_args", None):
                    handler.args_set.set()
            except Exception:
                pass
        return True
    except Exception as e:
        logger.warning(f"Failed to bind voice conversation: {e}")
        return False


def create_voice_stream():
    """Create the FastRTC audio stream with VAD and ReplyOnPause."""
    try:
        from fastrtc import ReplyOnPause, Stream
    except ImportError:
        logger.warning(
            "Voice dependencies not installed. Install with: pip install -e './backend[voice]'"
        )
        return None

    # Must run before any aiortc PeerConnection is created so the patched
    # candidate gathering is in place. No-op unless WEBRTC_HOST_IP is set.
    from app.voice.docker_patch import apply_webrtc_docker_patch
    apply_webrtc_docker_patch()

    from app.llm.agent import get_agent
    from app.voice.stt import get_stt_model
    from app.voice.tts import get_tts_model
    from app.db.engine import get_session_factory
    from app.db.repositories.conversation import add_message

    config = get_config()
    if not config.voice.enabled:
        logger.info("Voice is disabled in config")
        return None

    stt_model = get_stt_model()
    tts_model = get_tts_model()
    agent = get_agent()
    factory = get_session_factory()

    def handle_audio(audio, conversation_id: str):
        """Called by ReplyOnPause when user stops speaking.

        `conversation_id` is set per-connection via `/api/voice/bind` before
        audio starts flowing (fastrtc's ReplyOnPause blocks on args via
        `wait_for_args_sync`, so there is no race with the first utterance).
        """
        if not conversation_id:
            logger.warning("[voice] No conversation_id bound; dropping utterance")
            return

        # STT: audio -> text
        transcript = stt_model.stt(audio)
        logger.debug(f"[voice] ({conversation_id}) Transcript: {transcript}")

        if not transcript or len(transcript.strip()) < 2:
            return

        # Save user message
        db = factory()
        try:
            add_message(db, conversation_id, "user", transcript)
        finally:
            db.close()

        # Stream agent response with sentence-level TTS
        content_buffer = ""
        full_response = ""

        for event_type, data in agent.stream(transcript, thread_id=conversation_id):
            if event_type == "chunk" and data:
                content_buffer += data
                full_response += data

                if data and data[-1] in ".!?,;:":
                    logger.debug(f"[voice] TTS: {content_buffer}")
                    for audio_chunk in tts_model.stream_tts_sync(content_buffer):
                        yield audio_chunk
                    content_buffer = ""

            elif event_type == "done":
                if content_buffer.strip():
                    for audio_chunk in tts_model.stream_tts_sync(content_buffer):
                        yield audio_chunk

        # Save assistant message
        if full_response:
            db = factory()
            try:
                add_message(db, conversation_id, "assistant", full_response)
            finally:
                db.close()

        logger.debug(f"[voice] Response: {full_response[:100]}...")

    stream = Stream(
        ReplyOnPause(handle_audio),
        modality="audio",
        mode="send-receive",
        # fastrtc defaults to 1 — any not-yet-cleaned-up previous peer
        # connection then rejects the next offer with concurrency_limit_reached,
        # which in practice means "Voice UI closes as soon as clicked" the
        # second time. Raise it so lingering PCs don't block new sessions.
        concurrency_limit=10,
    )

    return stream


def mount_voice_stream(app):
    """Mount the voice stream onto a FastAPI app."""
    global _voice_stream

    config = get_config()
    if not config.voice.enabled:
        logger.info("Voice disabled, skipping WebRTC mount")
        return

    try:
        stream = create_voice_stream()
        if stream is not None:
            stream.mount(app)
            _voice_stream = stream
            logger.info("Voice WebRTC stream mounted on FastAPI app")
    except Exception as e:
        logger.warning(f"Failed to mount voice stream: {e}. Voice will be unavailable.")
