import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.engine import get_db
from app.db.repositories.conversation import add_message, create_conversation, get_conversation
from app.llm.agent import get_agent
from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/api", tags=["chat"])
chat_history = []

@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    agent = get_agent()

    # Get or create conversation
    if request.conversation_id:
        conv = get_conversation(db, request.conversation_id)
        if conv is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        conv = create_conversation(db)

    # Save user message
    add_message(db, conv.id, "user", request.message)

    # Get response
    response_text = agent.invoke(request.message, thread_id=conv.id)

    # Save assistant message
    msg = add_message(db, conv.id, "assistant", response_text)

    return ChatResponse(
        response=response_text,
        conversation_id=conv.id,
        message_id=msg.id,
    )


@router.post("/chat/stream")
def chat_stream(request: ChatRequest, db: Session = Depends(get_db)):
    agent = get_agent()

    # Get or create conversation
    if request.conversation_id:
        conv = get_conversation(db, request.conversation_id)
        if conv is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        conv = create_conversation(db)

    # Save user message
    add_message(db, conv.id, "user", request.message)
    chat_history = [{"role": "user", "content": request.message}]

    def event_stream():
        full_response = ""
        

        for event_type, data in agent.stream(request.message, history=chat_history, thread_id=conv.id):
            if event_type == "chunk":
                full_response += data
                yield f"data: {json.dumps({'type': 'chunk', 'content': data})}\n\n"
            elif event_type == "tool_call":
                yield f"data: {json.dumps({'type': 'tool_call', 'name': data['name'], 'args': data['args']})}\n\n"
            elif event_type == "tool_result":
                yield f"data: {json.dumps({'type': 'tool_result', 'name': data['name'], 'content': data['content']})}\n\n"
            elif event_type == "done":
                # Save the full response
                msg = add_message(db, conv.id, "assistant", full_response)
                chat_history.append({"role": "assistant", "content": full_response})
                yield f"data: {json.dumps({'type': 'done', 'message_id': msg.id, 'conversation_id': conv.id, 'full_content': full_response})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
