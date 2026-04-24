# Episode 1 — I Built My Own ChatGPT That Runs on My Laptop (No API)

**Role in series:** Channel launcher. Full demo + repo tour. Sets the "local-first, self-owned AI" positioning for the whole series.

**Target length:** ~10 minutes.

**One-line promise to viewer:** By the end of this series you'll have your own ChatGPT clone — voice, text, memory, tools — that you own and run locally.

---

## Pre-production checklist

- [ ] Jarvis running locally, voice mode tested, at least 2 seeded conversations (one with Mom-named contact for the demo line)
- [ ] Terminal ready with `docker-compose up` typed but not run (for the money shot)
- [ ] DevTools → Network tab pinned open (proves no cloud calls)
- [ ] Excalidraw / whiteboard with the 4-box architecture pre-drawn but hidden
- [ ] Good mic (this is a voice-AI video — bad audio kills trust instantly)
- [ ] Face cam on for cold open and CTA, screen-only for demo sections
- [ ] GitHub repo pinned comment copy written in advance

## Thumbnail + title

- **Title:** `I Built My Own ChatGPT That Runs on My Laptop (No API Key)`
- **Thumbnail:** your face (surprised/confident) + big contrast text `NO API KEY` + Jarvis UI visible in the corner
- **A/B test:** swap `NO API KEY` ↔ `100% LOCAL` on 3 different thumbnails

---

## Full script

### 0:00 – 0:15 · COLD OPEN

*(Camera on you. Jarvis voice mode is open on screen behind you.)*

> "Hey Jarvis — what's the weather in Tokyo?"

*(Jarvis responds in voice.)*

> "Open my last conversation with Mom."

*(It pulls it up on screen.)*

> "Now imagine I told you this is running **entirely** on this laptop. No OpenAI. No Anthropic. No internet. Just me, Python, and about 400 lines of the right code. Let me show you how I built it."

**Why this works:** visceral proof in the first 10 seconds. The "no internet" twist is the retention spike.

### 0:15 – 0:45 · HOOK + PROMISE

> "In this series, we're building a full ChatGPT clone from scratch — voice, text, memory, tools, the works. By episode 10 you'll have your own AI assistant you actually own. No subscriptions. No rate limits. Today is the overview — what we're building, why, and the one architectural decision that makes all of this possible."

### 0:45 – 1:30 · WHY (emotional)

> "I got tired of three things. One — paying $20 a month for something I couldn't customize. Two — my conversations living on someone else's server. And three — waiting three seconds for a voice response when I know the model can do it in under one. So I built Jarvis. And I'm going to teach you every single piece."

### 1:30 – 4:30 · THE DEMO (the meat)

Show, don't tell. Order matters:

1. **Text chat** — type a message, show streaming response token-by-token
2. **Voice mode** — click the voice button, have a natural back-and-forth, demonstrate interrupting it mid-sentence (barge-in)
3. **Tool call** — ask something that triggers web search, show the tool-call bubble appearing live
4. **Proof it's local** — cut to DevTools Network tab showing zero external requests; cut to terminal showing Ollama running
5. **The money shot** — close everything, type `docker-compose up`, show it all spinning up with one command

### 4:30 – 7:00 · THE ARCHITECTURE

Pull up Excalidraw. Four boxes only. Don't over-explain.

```
Browser  →  FastAPI  →  LangGraph Agent  →  LLM + Tools + Voice
```

> "That's it. Everything we build for the next 9 episodes fits inside these four boxes. The browser talks to FastAPI over WebSocket for text and WebRTC for voice. FastAPI hands the message to a LangGraph agent, which decides whether to call a tool, hit the LLM, or both. Everything streams back the way it came. If you understand these four boxes, you understand the whole system."

### 7:00 – 8:00 · WHAT YOU'LL NEED

Keep it brief, on-screen bullets:

- Python 3.11
- Node 20
- Docker
- 16GB RAM (for local models) **or** any API key if you want faster iteration
- The GitHub repo (link in description + pinned comment)

> "If you don't have 16 gigs of RAM, don't worry — in episode 9 I'll show you how to swap in OpenAI or Claude with one line of config."

### 8:00 – 9:30 · ROADMAP TEASER

Flash the 10-episode list on screen, voice-over highlights:

> "Episode 2 — we wire up the agent brain and get streaming chat working. Episode 3 — we give it a voice that sounds eerily human, running locally. Episode 4 — real-time voice with WebRTC, the part nobody explains properly. And by episode 10 we ship the whole thing in Docker so you can run it anywhere."

### 9:30 – end · CTA

> "Subscribe so you don't miss episode 2 — it drops this week. And drop a comment telling me what **you'd** name your assistant. I'll build the top-voted one into the series. See you in episode 2."

---

## B-roll / cutaway shot list

- Close-up of hands on keyboard during the demo
- Screen zoom on `docker-compose up` output
- Screen zoom on the empty Network tab (proof of local)
- Quick pan across the GitHub repo file tree
- Tight shot on the voice-mode UI pulsing while Jarvis speaks

## Pinned comment (post immediately on publish)

```
📂 Full source code: https://github.com/<your-handle>/jarvis
📺 Episode 2 drops <day> — hit subscribe
💬 What would YOU name your AI? Top comment goes in the series.
```

## Shorts to cut from this episode

1. **The "no internet" reveal** (0:00–0:25) — the cold open, end on the laptop
2. **The `docker-compose up` money shot** (4:15–4:45) — satisfying, screen-only
3. **Why I stopped paying $20/month** (0:45–1:10) — relatable, face-cam

## Cross-post plan (day of publish)

- r/LocalLLaMA — title: "Built my own ChatGPT that runs 100% locally — full series on how I did it"
- r/selfhosted — title: "Self-hosted voice + text AI assistant (FastAPI + LangGraph + Ollama)"
- Hacker News — "Show HN: Jarvis – a local-first ChatGPT clone with real-time voice"
- X/Twitter — 30-second clip of the voice demo + repo link
