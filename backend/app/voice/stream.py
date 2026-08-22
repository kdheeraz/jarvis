import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from loguru import logger

from app.config import get_config
from app.memory import mneme
from app.voice.text import strip_markdown_for_speech

# Per-connection voice conversation mapping is handled by fastrtc's
# per-handler `set_args` — we keep a reference to the mounted Stream so
# the bind endpoint can push conversation_id into the right connection.
_voice_stream: Any | None = None

_recall_executor = ThreadPoolExecutor(max_workers=2)

# Per-conversation cache of the last recalled memory block. Recall does a
# ~0.8s network + vector search, so running it inline would delay every reply.
# Instead each turn uses the context recalled on the PREVIOUS turn (instant)
# and refreshes in the background for the next one — a one-turn lag traded for
# a snappier response. First turn of a conversation has no memory yet.
_recall_cache: dict[str, str] = {}

# TTS flush sizing (see the streaming loop in handle_audio). Anything shorter
# than _CHUNK_MIN_CHARS isn't worth its own Piper utterance; the first flush of
# a turn may break at a clause instead of a sentence, but only once it has
# _FIRST_CHUNK_MIN_CHARS of text so it doesn't ship a bare "Okay,".
_CHUNK_MIN_CHARS = 2
_FIRST_CHUNK_MIN_CHARS = 25


def _refresh_recall_async(conversation_id: str, transcript: str) -> None:
    """Recall memory in the background and stash it for the next turn."""
    def _run():
        try:
            _recall_cache[conversation_id] = mneme.recall(transcript)
        except Exception as e:
            logger.warning(f"[voice] background recall failed: {e}")

    _recall_executor.submit(_run)


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


def _interrupt_on_speech_start(reply_on_pause_cls):
    """Build a ReplyOnPause subclass that stops speaking as soon as you start.

    Stock fastrtc only acts on a barge-in inside `if self.state.pause_detected`,
    i.e. once the user has FINISHED their interrupting sentence and a further
    near-silent chunk has gone by. While the assistant is mid-reply that reads
    as "it keeps talking over me, then answers late".

    `determine_pause` already flips `state.started_talking` on the first chunk
    holding more than `started_talking_threshold` seconds of speech, and
    `emit()` re-creates the state (`state.new()`) for every reply, so that flag
    has a clean rising edge per turn. Cutting the reply on that edge stops the
    assistant while the user is still talking, which is the behaviour people
    expect. Deliberately NOT touched here: `state.stream`, which is accumulating
    the barge-in utterance and is what the next generator gets fed.
    """

    class ReplyOnPauseInterruptOnSpeech(reply_on_pause_cls):
        def receive(self, frame) -> None:
            if self.state.responding and not self.can_interrupt:
                return

            was_talking = self.state.started_talking
            self.process_audio(frame, self.state)

            if (
                self.can_interrupt
                and self.state.responding
                and self.state.started_talking
                and not was_talking
            ):
                logger.debug("[voice] barge-in: user started talking, cutting reply")
                self._close_generator()
                self.generator = None
                self.clear_queue()

            if self.state.pause_detected:
                self.event.set()
                if self.can_interrupt and self.state.responding:
                    self._close_generator()
                    self.generator = None
                if self.can_interrupt:
                    self.clear_queue()

    return ReplyOnPauseInterruptOnSpeech


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
    agent = get_agent()
    factory = get_session_factory()

    # Pre-warm the TTS model at mount so the first utterance doesn't eat the
    # cold-load cost (e.g. Kokoro takes ~30s to initialize) as dead silence.
    # We deliberately do NOT keep this reference — handle_audio re-fetches via
    # get_tts_model() each utterance so a voice change saved in the admin UI
    # (which calls reset_tts_model()) still takes effect without a restart.
    get_tts_model()

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

        # Recall relevant long-term memory (Mneme) and prepend it as context for
        # this turn. Best-effort: returns "" if memory is disabled or unavailable.
        # Use memory recalled on the previous turn (instant) and refresh in the
        # background — keeps the ~0.8s recall off the critical path.
        mem_block = _recall_cache.get(conversation_id, "")
        agent_input = f"{mem_block}\n\nUser: {transcript}" if mem_block else transcript
        _refresh_recall_async(conversation_id, transcript)

        # Fetch the TTS model fresh each utterance so voice/engine changes saved
        # via the admin UI (which call reset_tts_model()) take effect without a
        # restart. get_tts_model() returns the cached singleton, so this is cheap.
        tts_model = get_tts_model()

        # Stream agent response with sentence-level TTS.
        #
        # Each stream_tts_sync() call is an independent Piper utterance with its
        # own prosody and leading/trailing padding, so every flush is an audible
        # seam. Flushing on commas therefore turned "Okay, safe travels!" into
        # three separate utterances — staccato. Flush on sentence ends only, with
        # one exception: before any audio has gone out we also accept a clause
        # break, so time-to-first-audio stays low on long replies.
        content_buffer = ""
        full_response = ""
        spoke_yet = False

        def speak(text: str):
            """Synthesize one buffer, skipping fragments with nothing to say.

            Markdown is stripped first — the agent is shared with text chat and
            emits `**bold**`, bullets and headings, which Piper reads out as
            "asterisk asterisk". Only the spoken copy is stripped; `full_response`
            keeps its markdown for the UI and the stored message."""
            text = strip_markdown_for_speech(text)
            if not any(ch.isalnum() for ch in text):
                return
            logger.debug(f"[voice] TTS: {text}")
            yield from tts_model.stream_tts_sync(text)

        try:
            for event_type, data in agent.stream(agent_input, thread_id=conversation_id):
                if event_type == "chunk" and data:
                    content_buffer += data
                    full_response += data

                    pending = content_buffer.strip()
                    sentence_end = data[-1] in ".!?"
                    early_clause = (
                        not spoke_yet
                        and data[-1] in ",;:"
                        and len(pending) >= _FIRST_CHUNK_MIN_CHARS
                    )
                    if (sentence_end or early_clause) and len(pending) >= _CHUNK_MIN_CHARS:
                        yield from speak(content_buffer)
                        spoke_yet = True
                        content_buffer = ""

                elif event_type == "done":
                    if content_buffer.strip():
                        yield from speak(content_buffer)
        except Exception as e:
            # The LLM call failed (rate limit, network, etc.). Speak a short
            # apology so the UI gets audio back and leaves "listening" instead
            # of hanging silently, and log a concise reason (no full traceback).
            logger.warning(f"[voice] agent failed; speaking fallback: {e}")
            fallback = "Sorry, I ran into a problem reaching my brain just now. Please try again in a moment."
            try:
                for audio_chunk in tts_model.stream_tts_sync(fallback):
                    yield audio_chunk
            except Exception as tts_e:
                logger.error(f"[voice] fallback TTS also failed: {tts_e}")
            return

        # Save assistant message
        if full_response:
            db = factory()
            try:
                add_message(db, conversation_id, "assistant", full_response)
            finally:
                db.close()

        # Store this turn's user message in long-term memory (fire-and-forget).
        # remember() runs a ~60s LLM ingest, so push it to a background thread
        # rather than blocking this worker before the next utterance.
        threading.Thread(target=mneme.remember, args=(transcript,), daemon=True).start()

        logger.debug(f"[voice] Response: {full_response[:100]}...")

    # VAD tuning so fan/handling noise doesn't trigger phantom utterances or
    # cut off the assistant mid-reply. All values come from config.voice.vad.
    from fastrtc import SileroVadOptions
    from fastrtc.reply_on_pause import AlgoOptions

    vad = config.voice.vad
    algo_options = AlgoOptions(
        audio_chunk_duration=vad.audio_chunk_duration,
        started_talking_threshold=vad.started_talking_threshold,
        speech_threshold=vad.speech_threshold,
    )
    model_options = SileroVadOptions(
        threshold=vad.threshold,
        min_speech_duration_ms=vad.min_speech_duration_ms,
        min_silence_duration_ms=vad.min_silence_duration_ms,
        speech_pad_ms=vad.speech_pad_ms,
    )
    logger.info(
        f"[voice] VAD: threshold={vad.threshold} "
        f"min_speech_ms={vad.min_speech_duration_ms} "
        f"min_silence_ms={vad.min_silence_duration_ms} "
        # chunk_s and started_talking are the two that actually govern
        # turn-end and barge-in sensitivity — log them or tuning is guesswork.
        f"chunk_s={vad.audio_chunk_duration} "
        f"started_talking={vad.started_talking_threshold} "
        f"speech={vad.speech_threshold} "
        f"can_interrupt={vad.can_interrupt}"
    )

    stream = Stream(
        _interrupt_on_speech_start(ReplyOnPause)(
            handle_audio,
            algo_options=algo_options,
            model_options=model_options,
            can_interrupt=vad.can_interrupt,
        ),
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
