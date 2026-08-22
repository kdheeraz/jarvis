import asyncio
import json
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger

from app.db.engine import get_session_factory
from app.db.repositories.conversation import add_message, create_conversation, get_conversation
from app.llm.agent import get_agent
from app.memory import mneme

router = APIRouter()

_executor = ThreadPoolExecutor(max_workers=4)

_STREAM_DONE = object()


async def _aiter_sync_stream(gen_factory):
    """Bridge a blocking generator into an async iterator without draining it first.

    `agent.stream()` is a synchronous generator; running it to completion in a
    thread (e.g. `list(agent.stream(...))`) would buffer the whole reply before
    the first token reaches the browser, killing the real-time feel. Instead we
    run the generator in a worker thread and hand each item to the event loop as
    soon as it is produced, so chunks are forwarded token-by-token.
    """
    loop = asyncio.get_event_loop()
    queue: asyncio.Queue = asyncio.Queue()

    def _produce():
        try:
            for item in gen_factory():
                loop.call_soon_threadsafe(queue.put_nowait, item)
        except Exception as exc:  # surface producer errors to the consumer
            loop.call_soon_threadsafe(queue.put_nowait, ("__error__", exc))
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, _STREAM_DONE)

    loop.run_in_executor(_executor, _produce)

    while True:
        item = await queue.get()
        if item is _STREAM_DONE:
            return
        if isinstance(item, tuple) and item and item[0] == "__error__":
            raise item[1]
        yield item


@router.websocket("/ws/chat/{conversation_id}")
async def websocket_chat(websocket: WebSocket, conversation_id: str):
    await websocket.accept()
    logger.info(f"WebSocket connected: conversation={conversation_id}")

    factory = get_session_factory()
    db = factory()

    try:
        # Get or create conversation
        if conversation_id == "new":
            conv = create_conversation(db)
            conversation_id = conv.id
            await websocket.send_json({
                "type": "conversation_created",
                "conversationId": conv.id,
            })
        else:
            conv = get_conversation(db, conversation_id)
            if conv is None:
                await websocket.send_json({"type": "error", "message": "Conversation not found"})
                await websocket.close()
                return

        agent = get_agent()
        loop = asyncio.get_event_loop()

        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)

            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            if data.get("type") != "message":
                continue

            content = data.get("content", "").strip()
            if not content:
                continue

            # Save user message
            add_message(db, conversation_id, "user", content)

            # Send thinking status
            await websocket.send_json({"type": "status", "message": "Thinking..."})

            # Recall relevant long-term memory (Mneme) and prepend it as context for this turn.
            # Best-effort: returns "" if memory is disabled or unavailable.
            mem_block = await loop.run_in_executor(_executor, mneme.recall, content)
            agent_input = f"{mem_block}\n\nUser: {content}" if mem_block else content

            # Stream the agent's reply token-by-token. _aiter_sync_stream pumps
            # the blocking generator from a worker thread and forwards each event
            # as it arrives, so the browser sees chunks live instead of one burst.
            full_response = ""

            stream = _aiter_sync_stream(
                lambda: agent.stream(agent_input, thread_id=conversation_id)
            )

            async for event_type, event_data in stream:
                if event_type == "chunk":
                    full_response += event_data
                    await websocket.send_json({"type": "chunk", "content": event_data})
                elif event_type == "tool_call":
                    tool_name = event_data["name"]
                    friendly = _tool_status(tool_name, event_data.get("args", {}))
                    await websocket.send_json({"type": "status", "message": friendly})
                    await websocket.send_json({
                        "type": "tool_call",
                        "name": tool_name,
                        "args": event_data["args"],
                    })
                elif event_type == "tool_result":
                    await websocket.send_json({
                        "type": "tool_result",
                        "name": event_data["name"],
                        "content": event_data["content"],
                    })
                elif event_type == "done":
                    msg = add_message(db, conversation_id, "assistant", full_response)
                    await websocket.send_json({
                        "type": "done",
                        "messageId": msg.id,
                        "fullContent": full_response,
                    })
                    # Store this turn's user message in long-term memory (fire-and-forget).
                    loop.run_in_executor(_executor, mneme.remember, content)

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: conversation={conversation_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        db.close()


def _tool_status(tool_name: str, args: dict) -> str:
    """Generate a friendly status message for tool usage."""
    if tool_name == "rag_search":
        query = args.get("query", "")
        return f"Searching documents for \"{query[:50]}\"..."
    elif tool_name == "web_search":
        query = args.get("query", "")
        return f"Searching the web for \"{query[:50]}\"..."
    elif tool_name == "calculator":
        return "Calculating..."
    elif tool_name == "datetime_tool":
        return "Checking date/time..."
    return f"Using {tool_name}..."
