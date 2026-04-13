from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from typer import prompt
from langchain_ollama import ChatOllama

from langchain.agents import create_agent
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from typing import Callable
from langgraph.checkpoint.memory import InMemorySaver  


from tools import web_search

tool_map ={"web_search": web_search}

class ChatBase:
    def __init__(self, llm, prompt):
        self.llm = llm
        self.prompt = prompt
        self.chain = prompt | llm
    def chat(self, user_input, chat_history=[]):
        response = self.chain.invoke({"input": user_input, "chat_history": chat_history or []})
        if response.tool_calls:
            print(f"Tool calls detected: {response.tool_calls}")
            for tool_call in response.tool_calls:
                name=tool_call["name"]
                arges=tool_call["args"]
                kwargs=tool_call.get("kwargs", {})
                if name in tool_map:
                    tool_func = tool_map[name]
                    tool_result = tool_func(*arges, **kwargs)
                    print(f"Tool '{name}' returned: {tool_result}")
                    # Add tool result to history
                    chat_history.append({
                        "role": "assistant",
                        "content": response.content,
                        "tool_calls": response.tool_calls
                    })
                    chat_history.append({
                        "role": "tool",
                        "name": name,
                        "content": tool_result
                    })
                    # Get follow-up response from model with tool results
                    followup_response = self.chain.invoke({"input": user_input, "chat_history": chat_history})
                    return followup_response
                else:
                    print(f"Tool '{name}' not found in tool_map.")
                    return response
        # Update history with the interaction

        chat_history.extend([
            HumanMessage(content=user_input),
            AIMessage(content=response.content)
        ])
        print(f"User: {user_input}")
        print(f"AI: {response.content}")
        return response

    def stream_chat(self, user_input, chat_history=[], tools=None):
        # Stream the response
        full_response = ""
        for chunk in self.chain.stream({"input": user_input, "chat_history": chat_history or []}):
            content = chunk.content
            print(content, end="", flush=True)
            yield chunk
            full_response += content
        
        # Update history with the interaction
        chat_history.extend([
            HumanMessage(content=user_input),
            AIMessage(content=full_response)
        ])
        print("\n")


class CustomChatOllama(ChatBase):
    def __init__(self, model,prompt, temperature=0, base_url="http://127.0.0.1:11434", tools=[]):
        llm = ChatOllama(model=model, temperature=0, base_url="http://127.0.0.1:11434",prompt=prompt)
        super().__init__(llm, prompt)


class AgentChat:
    def __init__(self, model,prompt, temperature=0, base_url="http://127.0.0.1:11434", tools=[]):
        self.llm = ChatOllama(model=model, temperature=0, base_url="http://127.0.0.1:11434")
        self.agent = create_agent(model=self.llm, tools=tools, system_prompt=prompt, checkpointer=InMemorySaver())
    def chat(self, user_input, chat_history=[]):
        response = self.agent.invoke({"messages": chat_history + [HumanMessage(content=user_input)]})
        print(f"User: {user_input}")
        print(f"AI: {response}")
        ai_message = response["messages"][-1]
        chat_history.append(HumanMessage(content=user_input))
        chat_history.append(AIMessage(content=ai_message.content))
        return ai_message.content
    def stream_chat(self, user_input, chat_history=[], tools=None):
        full_response = ""
        content_to_stream = ""
        is_tool=False
        print("Chat history for this turn:")
        for msg in chat_history:
            print(f" {msg.content}")
        for chunk in self.agent.stream({"messages": chat_history + [HumanMessage(content=user_input)]},  {"configurable": {"thread_id": "1"}}, stream_mode="messages"):
            print(f"Chunk received: {chunk}")
            ai_message_chunk = chunk[0]
            if isinstance(ai_message_chunk, ToolMessage):
                content = "Getting tool results..."
                #is_tool = False
            elif ai_message_chunk.tool_calls:
                content= "Wait a moment, loading more information..."
                is_tool = True
            elif ai_message_chunk.content: 
                content = ai_message_chunk.content   
            yield content    
            full_response += content
            content=""
        chat_history.append(HumanMessage(content=user_input))
        chat_history.append(AIMessage(content=full_response))


