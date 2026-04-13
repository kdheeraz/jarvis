# Jarvis Architecture — UI → DB

End-to-end request flow for both text and voice, plus where each concern lives.

## Components

| Layer | Path | Role |
|---|---|---|
| Browser UI | `frontend/src` | React + Zustand store, routing, voice hook |
| API (REST) | `backend/app/api` | Auth, conversations, voice bind, admin |
| Chat WS | `backend/app/ws/chat.py` | Streaming text chat over WebSocket |
| Voice WebRTC | `backend/app/voice/stream.py` | fastrtc `Stream` mounted on FastAPI |
| Agent | `backend/app/llm/agent.py` | LangGraph agent, tools, streaming |
| Repositories | `backend/app/db/repositories` | `create_conversation`, `add_message`, … |
| DB | `data/jarvis.db` (SQLite) | `conversations`, `messages` tables |

---

## Text chat flow

```
 Browser (React)                                Backend                           DB
 ──────────────                                  ────────                         ──
 ChatInput.send ── addMessage(user) ──► chatStore
                    │
                    └─► useWebSocket.sendMessage
                           │
                           └── WS /ws/chat/{conversation_id} ── ws/chat.py
                                                                   │
                                                                   ├─ create_conversation (if "new")
                                                                   │     │
                                                                   │     └───────────────────► conversations
                                                                   │
                                                                   ├─ add_message("user", …) ──► messages
                                                                   │
                                                                   ├─ agent.stream(…)  (LangGraph + tools)
                                                                   │     │
                                                                   │     └─► chunks / tool_call / tool_result
                                                                   │
                                                                   ├─ send chunks back over WS ──► chatStore.updateLastMessage
                                                                   │
                                                                   └─ add_message("assistant", …) ► messages
                                                                                                           │
 chatStore.markLastMessageDone ◄── done event ◄─────────────────────────────────────────────────────────────┘
```

**Key files**
- `frontend/src/hooks/useWebSocket.ts` — event switch for `chunk` / `tool_call` / `done`, drops empty assistant bubble on `tool_call`.
- `frontend/src/store/chatStore.ts` — single source of truth for sidebar list, active conversation, and message array.
- `backend/app/ws/chat.py` — runs `agent.stream` in a thread pool, forwards events to the WS.
- `backend/app/db/repositories/conversation.py` — `create_conversation`, `get_conversation`, `add_message`, `list_conversations`.

---

## Voice flow (WebRTC)

```
 Browser                                          Backend (fastrtc Stream)                     DB
 ───────                                          ────────────────────────                     ──
 Mic ─► RTCPeerConnection
   │
   ├── POST /webrtc/offer {sdp, webrtc_id} ──► Stream.handle_offer
   │                                               │
   │                                               ├─ handlers[webrtc_id] = ReplyOnPause.copy()
   │                                               └─ connections[webrtc_id] = [AudioCallback, …]
   │
   ├── POST /api/voice/bind {webrtc_id, conversation_id} ──► app/api/voice.py
   │                                               │
   │                                               ├─ create_conversation("Voice chat") if none
   │                                               ├─ stream.set_input(webrtc_id, conversation_id)
   │                                               │     │
   │                                               │     └─► handler.latest_args = ["__webrtc_value__", conv_id]
   │                                               │         handler.args_set.set()
   │                                               │
   │                                               └─ _make_args_persistent(handler)
   │                                                     (overrides reset() to re-arm args_set)
   │
   └── SRTP audio frames ─► AudioCallback ─► ReplyOnPause.emit
                                                   │
                                                   ├─ VAD detects pause
                                                   ├─ wait_for_args_sync()  (no-op, args_set already set)
                                                   ├─ fn(audio, conversation_id) = handle_audio
                                                   │     │
                                                   │     ├─ STT (distil-whisper) ─► transcript
                                                   │     ├─ add_message("user", transcript) ──► messages
                                                   │     ├─ agent.stream(transcript, thread_id=conv_id)
                                                   │     │     │
                                                   │     │     └─► chunks buffered to sentence boundary
                                                   │     │           │
                                                   │     │           └─► TTS (piper) ─► audio frames
                                                   │     └─ add_message("assistant", full_response) ──► messages
                                                   │
 Speaker ◄─ audio frames ◄──────────────────────────┘

 When user closes overlay:
   ChatPage effect detects isActive false ─► setActiveConversation(id) (refetches from DB)
                                          ─► loadConversations (refreshes sidebar)
```

**Key files**
- `frontend/src/hooks/useVoiceMode.ts` — creates the PC, sends offer, POSTs bind, exposes `rebind` for mid-session conversation switching.
- `frontend/src/pages/ChatPage.tsx` — threads `activeConversationId` into the voice hook, rebinds on sidebar switch, refetches messages on voice close.
- `backend/app/voice/stream.py` — handler, `bind_voice_conversation`, `_make_args_persistent` (fastrtc shim so additional args survive `reset()`).
- `backend/app/api/voice.py` — `/api/voice/bind` creates/validates the conversation and pushes args into the right connection.

**Why the `_make_args_persistent` shim exists**
fastrtc's `ReplyOnPause` supports "additional inputs" (params beyond audio) but assumes a Gradio UI re-pushes them every turn. In our mount-only setup, `StreamHandlerBase.reset()` (called after each utterance) clears `args_set`, which would make the next utterance block forever in `wait_for_args_sync`. The shim patches the handler instance so that after fastrtc's cleanup, the event is re-armed — keeping the already-bound `conversation_id` valid for every subsequent turn, per connection.

**Multi-session safety**
- `handlers` and `connections` are keyed by `webrtc_id`, so each concurrent voice session has its own `ReplyOnPause` instance, its own `latest_args`, and its own patched `reset`.
- Text chat is stateless per-request against the DB; LangGraph uses `thread_id=conversation_id` so memory is scoped per conversation.

---

## Data model

`conversations`
- `id` (uuid), `title`, `created_at`, `updated_at`

`messages`
- `id` (uuid), `conversation_id` (fk), `role` (user/assistant/tool/system), `content`, `created_at`

Both tables live in SQLite at `data/jarvis.db` (configurable via `config/config.yaml` → `database.url`, or the `DATABASE_URL` env var). Alembic migrations under `backend/alembic`.

Voice-created and text-created conversations share the same tables, which is why they interleave cleanly in the sidebar and why switching between voice and text on the same conversation "just works" — both paths call `add_message(conversation_id, role, content)` against the same row.

---

## Why a request can cross layers in both directions

- Text: browser → WS → agent → stream chunks back → DB write on `done`.
- Voice: browser → HTTP offer → WebRTC media in → handler (STT → agent → TTS) → WebRTC media out → DB writes interleaved → UI refetches on close.
- Voice bind: a one-shot HTTP POST that writes into the *in-memory* state of a specific fastrtc connection. No DB write except the optional `create_conversation`.

The only shared mutable state on the backend is `_voice_stream` (module-level handle to the mounted `Stream`) and fastrtc's own per-connection `handlers` / `connections` dicts. Everything else flows through repositories into SQLite.
