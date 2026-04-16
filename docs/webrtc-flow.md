# Voice / WebRTC End-to-End Flow

How the browser establishes a WebRTC peer connection with the FastAPI backend
when both sides are running under Docker, why the bridge network requires a
patch, and which ports / files are involved at each step.

---

## 1. Topology

```
                                     Docker host
 ┌──────────────┐   :3000  ┌──────────────────────────────────┐
 │   Browser    │ ───────► │ frontend container (nginx/vite)  │
 │  React SPA   │          │  - serves static SPA             │
 │              │          │  - reverse-proxies /api /ws      │
 │              │          │    /webrtc to backend:8000       │
 │  WebRTC PC   │          └──────────────────────────────────┘
 │  (mic + spk) │   :8000     ┌──────────────────────────────┐
 │              │ ──────────► │ backend container (uvicorn)  │
 │              │   HTTP/WS   │  FastAPI + fastrtc + aiortc  │
 │              │             └───────────────┬──────────────┘
 │              │                             │
 │              │   :7880-7889/udp (RTP+ICE)  │
 │              │ ◄───────────────────────────┘
 └──────────────┘
```

Three logical channels:

| Channel | Path on host | Container target | Purpose |
| --- | --- | --- | --- |
| HTTP   | `:3000/api/*`     | `frontend → backend:8000/api/*`   | REST (incl. `/api/voice/bind`) |
| WS     | `:3000/ws/*`      | `frontend → backend:8000/ws/*`    | Text chat streaming |
| WebRTC signalling | `:3000/webrtc/*` | `frontend → backend:8000/webrtc/*` | SDP offer/answer + ICE trickle |
| WebRTC media      | `:7880-7889/udp` (host) → `:7880-7889/udp` (backend) | direct UDP to backend container | RTP audio frames in both directions |

---

## 2. Why a Docker patch is needed

`aiortc` (used under the hood by `fastrtc`) gathers ICE host candidates by
enumerating the container's local interfaces. On Docker's default bridge
network, that yields only a `172.x.x.x` address. The browser on the host
cannot route to `172.x.x.x`, so ICE never completes and the peer connection
silently fails.

`backend/app/voice/docker_patch.py` monkey-patches
`aioice.ice.Connection.get_component_candidates` so that for every new peer
connection it:

1. Binds a UDP socket to `0.0.0.0` on the **first free port** in the
   `WEBRTC_UDP_PORT_MIN..WEBRTC_UDP_PORT_MAX` range (default `7880-7889`).
   A range — not a single pinned port — avoids `EADDRINUSE` when the previous
   connection's socket is still lingering.
2. Advertises `WEBRTC_HOST_IP` (e.g. `127.0.0.1`) as the candidate `host`
   address instead of the container's bridge IP.

The patch is a no-op unless `WEBRTC_HOST_IP` is set, so production
deployments can opt out (and use a TURN server instead, recommended for
multi-user scenarios — the port range caps concurrent peer connections).

The patch is invoked exactly once, lazily, from `create_voice_stream()` in
`backend/app/voice/stream.py:84-85` — **before** `fastrtc.Stream` constructs
its first `RTCPeerConnection`. A `_APPLIED` guard makes it idempotent.

---

## 3. Docker / port mapping

`docker-compose.yaml` (production):

```yaml
backend:
  ports:
    - "${BACKEND_PORT:-8000}:8000"      # FastAPI HTTP/WS
    - "7880-7889:7880-7889/udp"         # WebRTC media
  environment:
    - WEBRTC_HOST_IP=${WEBRTC_HOST_IP:-127.0.0.1}
    - WEBRTC_UDP_PORT_MIN=7880
    - WEBRTC_UDP_PORT_MAX=7889

frontend:
  ports:
    - "${FRONTEND_PORT:-3000}:80"       # nginx SPA + reverse proxy
```

`docker-compose.dev.yaml` overrides:

- `backend` runs the `dev` build target with `--reload`, mounts the source
  tree, exposes the same UDP range, and uses `config.docker.yaml`.
- `frontend` runs Vite dev server on `:3000` with proxies defined in
  `frontend/vite.config.ts:15-29` (`/api`, `/ws`, `/webrtc`, `/websocket`).

The required env vars (`WEBRTC_HOST_IP`, `WEBRTC_UDP_PORT_MIN/MAX`) and the
UDP port publish must agree — if they drift, the browser will receive ICE
candidates pointing at a port the host doesn't forward.

### nginx (production frontend)

`frontend/nginx.conf` proxies signalling traffic only:

```
location /webrtc/ { proxy_pass http://backend:8000/webrtc/; ... }
location /api/    { proxy_pass http://backend:8000/api/;    ... }
location /ws/     { proxy_pass http://backend:8000/ws/; Upgrade; Connection: upgrade; }
```

Media (UDP/RTP) does **not** go through nginx — it goes browser ⇄ host
`:7880-7889/udp` ⇄ backend container directly. nginx only proxies the
WebSocket signalling/control plane.

---

## 4. Backend startup sequence

1. `backend/app/main.py:create_app()` builds the FastAPI instance and calls
   `mount_voice_stream(app)` (`main.py:69-70`).
2. `mount_voice_stream` (`backend/app/voice/stream.py:172`) checks
   `config.voice.enabled`, then calls `create_voice_stream()`.
3. `create_voice_stream`:
   - Imports `fastrtc` (gracefully no-ops if missing).
   - Calls `apply_webrtc_docker_patch()` — must run **before** any
     `RTCPeerConnection` is instantiated.
   - Loads STT (`get_stt_model`), TTS (`get_tts_model`), and the LLM agent.
   - Builds `Stream(ReplyOnPause(handle_audio), modality="audio",
     mode="send-receive", concurrency_limit=10)`.
   - `concurrency_limit=10` (vs fastrtc's default 1) prevents lingering PCs
     from rejecting the next offer with `concurrency_limit_reached`, which
     manifested as "voice UI closes the second time you open it".
4. `stream.mount(app)` registers `fastrtc`'s WebRTC signalling endpoints
   under `/webrtc/*` on the FastAPI app and stores the stream in module
   global `_voice_stream` so `/api/voice/bind` can reach it.

---

## 5. Per-session flow (browser opens voice mode)

The frontend hook is `frontend/src/hooks/useVoiceMode.ts`. The end-to-end
sequence when the user clicks the mic icon:

```
Browser                                       Backend
───────                                       ───────
1. getUserMedia({audio})                         (no traffic)
2. webrtc_id = random()
3. new RTCPeerConnection({stun:google})
4. addTrack(mic), createDataChannel("text")
5. createOffer() → setLocalDescription(offer)
6. POST /webrtc/offer {sdp, type, webrtc_id} ─► fastrtc.Stream handler
                                                 - creates server-side PC
                                                 - patched candidate gather:
                                                   binds UDP in 7880-7889
                                                   advertises WEBRTC_HOST_IP
                                                 - sets remote desc, answers
   ◄─ {sdp, type:"answer"}
7. setRemoteDescription(answer)

   ICE trickle (in parallel):
   onicecandidate → POST /webrtc/offer
       {candidate, webrtc_id, type:"ice-candidate"}

8. ICE connectivity checks (UDP) ◄════════════► host :7880-7889/udp
   STUN binding via Google's stun.l.google.com  (server-reflexive candidate
                                                  discovered by browser)
   Host candidate from server == WEBRTC_HOST_IP:<port-in-range>
   → browser dials forwarded Docker port directly

9. connectionState === "connected"
   state = "listening"

10. POST /api/voice/bind {webrtc_id, conversation_id?}
    ─────────────────────────────────────────────►  backend/app/api/voice.py
                                                     - if no conversation_id,
                                                       create_conversation()
                                                     - bind_voice_conversation():
                                                       stream.set_input(
                                                         webrtc_id,
                                                         conversation_id)
                                                     - patches handler so
                                                       args survive across
                                                       fastrtc reset() calls
                                                       (see stream.py:17-41)
    ◄── {conversation_id, bound:true}

11. RTP audio (mic) ════════════════════════════►  ReplyOnPause VAD
                                                    - on pause: handle_audio
                                                    - STT → text
                                                    - persist user msg
                                                    - agent.stream(text)
                                                    - sentence-aware TTS
12. RTP audio (TTS) ◄═══════════════════════════
    ontrack handler plays <audio>, analyser
    flips state listening↔speaking
    DataChannel: {"type":"end_stream"} → state=listening
```

### Why the `bind` step exists separately from the offer

`fastrtc.ReplyOnPause` lets each handler take extra args (here:
`conversation_id`). Those args are pushed via `stream.set_input(webrtc_id,
...)`. The browser doesn't yet know the `conversation_id` at offer time
(the server may need to create it), and the WebRTC offer payload has no
slot for app-level metadata, so the binding is a separate REST call made
**immediately after** the answer is received.

`ReplyOnPause` blocks on `wait_for_args_sync()`, so even though the bind is
a separate HTTP roundtrip there is no race with the first utterance — audio
is buffered until the args arrive.

### Persistent-args patch

`fastrtc.StreamHandlerBase.reset()` (called after every utterance) clears
`args_set`. Because our handler has the extra `conversation_id` param,
`_needs_additional_inputs` is true and the next utterance would block
forever. `_make_args_persistent` (`stream.py:17-41`) wraps `reset` so that
after fastrtc's cleanup we re-set `args_set` from the still-valid
`latest_args`. Without this, voice works exactly once per session.

---

## 6. Configuration reference

| Env var | Default | Where used | Purpose |
| --- | --- | --- | --- |
| `WEBRTC_HOST_IP` | `127.0.0.1` (compose) / unset (skips patch) | `docker_patch.py:43` | Address advertised in ICE host candidates. |
| `WEBRTC_UDP_PORT_MIN` | `7880` | `docker_patch.py:48` | Lower bound of UDP range. |
| `WEBRTC_UDP_PORT_MAX` | `7889` | `docker_patch.py:49` | Upper bound (inclusive) — caps concurrent PCs. |
| `BACKEND_PORT` | `8000` | `docker-compose.yaml` | Host port for FastAPI (signalling). |
| `FRONTEND_PORT` | `3000` | `docker-compose.yaml` | Host port for nginx (or Vite in dev). |
| `VITE_PROXY_TARGET` | `http://backend:8000` (dev) / `http://localhost:8000` | `vite.config.ts:5` | Backend URL for Vite dev proxy. |
| `voice.enabled` (yaml) | `true` (in `config.docker.yaml`) | `stream.py:94`, `main.py:23` | Master switch — disables the entire WebRTC mount. |

For non-localhost deployments, set `WEBRTC_HOST_IP` to the public IP/hostname
of the Docker host. Also publish the same UDP range on that host's firewall.

---

## 7. Limitations and operational notes

- **Concurrency cap.** The number of simultaneous voice sessions equals
  `WEBRTC_UDP_PORT_MAX - WEBRTC_UDP_PORT_MIN + 1` (default 10). Beyond
  that, `get_component_candidates` returns `[]` and ICE fails.
- **No TURN.** Only a public Google STUN is configured client-side. NAT
  traversal works for typical home networks via the published UDP ports;
  symmetric NATs without direct UDP reachability will not connect. For
  multi-user / production deployments add a TURN server and remove the
  Docker patch in favour of TURN-relayed candidates.
- **nginx does not handle media.** Only signalling. RTP must reach the
  backend container directly via the published UDP ports.
- **`config.docker.yaml` vs `config.yaml`.** Compose dev/override sets
  `CONFIG_PATH=/app/config/config.docker.yaml` so the in-cluster service
  hostnames (`host.docker.internal` for Ollama, `chromadb`, `postgres`,
  etc.) resolve correctly.
- **Voice sessions create chats.** If `/api/voice/bind` is called without a
  `conversation_id` (or with `"new"`), the backend creates a conversation
  titled "Voice chat" so it appears in the sidebar like a text chat.

---

## 8. Files of interest

| Concern | File |
| --- | --- |
| Docker patch (ICE) | `backend/app/voice/docker_patch.py` |
| WebRTC stream + handler | `backend/app/voice/stream.py` |
| `/api/voice/bind` endpoint | `backend/app/api/voice.py` |
| App wiring (mounts stream) | `backend/app/main.py` |
| Browser side | `frontend/src/hooks/useVoiceMode.ts` |
| Voice UI overlay | `frontend/src/components/chat/VoiceModeOverlay.tsx` |
| nginx reverse proxy | `frontend/nginx.conf` |
| Vite dev proxy | `frontend/vite.config.ts` |
| Service / port wiring | `docker-compose.yaml`, `docker-compose.dev.yaml`, `docker-compose.override.yaml` |
| Backend image | `backend/Dockerfile` |
| Frontend image | `frontend/Dockerfile` |
