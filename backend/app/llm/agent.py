from typing import AsyncIterator, Optional
import uuid

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from loguru import logger

from app.config import get_config
from app.llm.factory import create_llm
from app.tools.registry import get_active_tools


class JarvisAgent:
    """Central agent that powers all chat modalities (REST, WebSocket, Voice)."""

    def __init__(self):
        self._config = get_config()
        self._llm = create_llm(self._config)
        self._tools = get_active_tools()
        self._checkpointer = MemorySaver()
        self._agent = self._build_agent()
        logger.info(
            f"JarvisAgent initialized: provider={self._config.llm.provider}, "
            f"tools={[t.name for t in self._tools]}"
        )

    def _build_agent(self):
        return create_react_agent(
            model=self._llm,
            tools=self._tools,
            checkpointer=self._checkpointer,
        )

    def rebuild(self):
        """Rebuild the agent with fresh config (called after config change)."""
        self._config = get_config()
        self._llm = create_llm(self._config)
        self._tools = get_active_tools()
        self._checkpointer = MemorySaver()
        self._agent = self._build_agent()
        logger.info("JarvisAgent rebuilt with updated config")

    def invoke(self, user_message: str, thread_id: str, history: list | None = None) -> str:
        """Synchronous invoke — returns full response text."""
        messages = self._prepare_messages(user_message, history)
        config = {"configurable": {"thread_id": thread_id}}

        result = self._agent.invoke({"messages": messages}, config)
        ai_message = result["messages"][-1]
        return ai_message.content

    def stream(self, user_message: str, thread_id: str, history: list | None = None):
        """Synchronous stream — yields (event_type, data) tuples."""
        messages = self._prepare_messages(user_message, history)
        config = {"configurable": {"thread_id": thread_id}}

        for chunk in self._agent.stream(
            {"messages": messages}, config, stream_mode="messages"
        ):
            msg = chunk[0]
            metadata = chunk[1] if len(chunk) > 1 else {}

            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tool_call in msg.tool_calls:
                    yield ("tool_call", {
                        "name": tool_call["name"],
                        "args": tool_call["args"],
                    })
            elif hasattr(msg, "type") and msg.type == "tool":
                yield ("tool_result", {
                    "name": getattr(msg, "name", ""),
                    "content": msg.content,
                })
            elif hasattr(msg, "content") and msg.content:
                yield ("chunk", msg.content)

        yield ("done", None)

    def _prepare_messages(self, user_message: str, history: list | None) -> list:
        messages = [SystemMessage(content=self._config.llm.system_prompt)]
        if history:
            messages.extend(history)
        messages.append(HumanMessage(content=user_message))
        return messages


# Singleton
_agent: Optional[JarvisAgent] = None


def get_agent() -> JarvisAgent:
    global _agent
    if _agent is None:
        _agent = JarvisAgent()
    return _agent


def rebuild_agent():
    global _agent
    if _agent is not None:
        _agent.rebuild()
    else:
        _agent = JarvisAgent()
