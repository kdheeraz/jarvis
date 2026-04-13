import sys
import argparse

from fastrtc import ReplyOnPause, Stream, get_tts_model#get_stt_model
from loguru import logger
from ollama import chat
from tools import web_search, tools

from distil_whisper_fastrtc import get_stt_model

# Create the model
whisper_model = get_stt_model()

stt_model = get_stt_model()  # whisper
tts_model = get_tts_model()  # kokoro

logger.remove(0)
logger.add(sys.stderr, level="DEBUG")

# Chat history
conversation_history = [
    {
        "role": "system",
        "content": "You are a helpful assistant named Friday in a call. Your goal is to demonstrate your capabilities in a succinct way. Your output will be converted to audio so don't include emojis or special characters in your answers. Respond to what the user said in a creative and helpful way. avoid using \"*\" or markdown in your response as it may cause issues in audio generation.",
    }
]

def stream_response(response):
    content_to_stream = ""
    full_response = ""
    for chunk in response:
        print(f"chunk: {chunk}")
        if "message" in chunk:
            response_text = chunk["message"]["content"]
            if response_text and response_text[-1] not in [".", "!", "?", ","]:
                content_to_stream += response_text
                full_response += response_text
            else:
                content_to_stream += response_text
                full_response += response_text
                logger.debug(f"🤖 Response: {content_to_stream}")
                for audio_chunk in tts_model.stream_tts_sync(content_to_stream):
                    yield audio_chunk
                content_to_stream = ""
    
    # Add assistant response to history
    if full_response:
        conversation_history.append({"role": "assistant", "content": full_response})

def echo(audio):
    transcript = stt_model.stt(audio)
    logger.debug(f"🎤 Transcript: {transcript}")
    
    # Add user message to history
    conversation_history.append({"role": "user", "content": transcript})
    
    response = chat(
        stream=True,
        tools=tools,
        model="qwen2.5:3b",
        messages=conversation_history,
        options={"num_predict": 200},
    )
    content_to_stream = ""
    full_response = ""
    for chunk in response:
        print(f"chunk: {chunk}")          
        if "message" in chunk:
            if tool_calls := chunk["message"].get("tool_calls"):
                logger.debug(f"🔧 Tool calls: {tool_calls}")
                for tool_call in tool_calls:
                    if tool_call["function"]["name"] == "web_search":
                        search_query = tool_call["function"]["arguments"].get("query")
                        search_results = web_search(search_query)
                        logger.debug(f"🔍 Search results for '{search_query}': {search_results[:200]}...")
                        
                        # Add tool result to history
                        conversation_history.append({
                            "role": "assistant",
                            "content": chunk["message"]["content"],
                            "tool_calls": tool_calls
                        })
                        conversation_history.append({
                            "role": "tool",
                            "tool_name": "web_search",
                            "content": search_results
                        })
                response_with_tools = chat(
                    stream=True,
                    model="qwen2.5:3b",
                    messages=conversation_history,
                    #tools=tools,
                    options={"num_predict": 200},
                )
                for tool_chunk in response_with_tools:
                    print(f"tool_chunk: {tool_chunk}")
                    if "message" in tool_chunk:
                        response_text = tool_chunk["message"]["content"]
                        if response_text and response_text[-1] not in [".", "!", "?", ","]:
                            content_to_stream += response_text
                            full_response += response_text
                        else:
                            content_to_stream += response_text
                            full_response += response_text
                            logger.debug(f"🤖 Response: {content_to_stream}")
                            for audio_chunk in tts_model.stream_tts_sync(content_to_stream):
                                yield audio_chunk
                            content_to_stream = ""       
                        
            response_text = chunk["message"]["content"]


            if response_text and response_text[-1] not in [".", "!", "?", ","]:
                content_to_stream += response_text
                full_response += response_text
            else:
                content_to_stream += response_text
                full_response += response_text
                logger.debug(f"🤖 Response: {content_to_stream}")
                for audio_chunk in tts_model.stream_tts_sync(content_to_stream):
                    yield audio_chunk
                content_to_stream = ""
    
    # Add assistant response to history
    if full_response:
        conversation_history.append({"role": "assistant", "content": full_response})    


def create_stream():
    return Stream(ReplyOnPause(echo), modality="audio", mode="send-receive")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Local Voice Chat Advanced")
    parser.add_argument(
        "--phone",
        action="store_true",
        help="Launch with FastRTC phone interface (get a temp phone number)",
    )
    args = parser.parse_args()

    stream = create_stream()

    if args.phone:
        logger.info("Launching with FastRTC phone interface...")
        stream.fastphone()
    else:
        logger.info("Launching with Gradio UI...")
        stream.ui.launch(share=True)
