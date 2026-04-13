from fastapi import FastAPI
from langchain_core.messages import HumanMessage, AIMessage
import numpy as np
from openai import BaseModel
from torch import Stream
from langchain_voice_agent_final import create_stream
from tools import web_search
from base_chat import AgentChat, CustomChatOllama
from with_lang_chain import jarvis_prompt, PROMPT

app = FastAPI()

ollma_chat = CustomChatOllama(model="qwen2.5:3b", temperature=0, base_url="http://127.0.0.1:11434", tools=[web_search], prompt=PROMPT)

agent = AgentChat(model="qwen2.5:3b", temperature=0, base_url="http://127.0.0.1:11434", tools=[web_search], prompt=jarvis_prompt)

@app.post("/chat")
def chat(query: str, chat_history: list[AIMessage, HumanMessage]):
    res=agent.chat(query, chat_history)
    return {"response": res, "chat_history": chat_history}

stream = create_stream(chat_instance=ollma_chat)
stream.mount(app)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)

