import sys
import argparse
import threading
import uuid
import gradio as gr
from langchain_ollama import OllamaLLM
from fastrtc import AdditionalOutputs, ReplyOnPause, Stream, get_tts_model
from loguru import logger
from base_chat import AgentChat
from piper_tts import PiperTTSModel
from distil_whisper_fastrtc import get_stt_model
from tools import web_search
from with_lang_chain import PROMPT, stream_chat, jarvis_prompt

tts_model = PiperTTSModel(
    model_path="./jarvis-high.onnx", 
    config_path="./en.json"
)

# Models
whisper_model = get_stt_model()
stt_model = get_stt_model()
#tts_model = my_piper
#get_tts_model()

logger.remove(0)
logger.add(sys.stderr, level="DEBUG")

model = OllamaLLM(
    model="qwen2.5:3b",
    base_url="http://127.0.0.1:11434",
)

# 🧠 Session store
sessions = {}

agent = AgentChat(model="qwen2.5:3b", temperature=0, base_url="http://127.0.0.1:11434", tools=[web_search], prompt=jarvis_prompt)

def create_stream(chat_instance):
    session_id = str(uuid.uuid4())

    # Per-session state
    interrupt_flag = threading.Event()
    conversation_history = []


    sessions[session_id] = {
        "interrupt_flag": interrupt_flag,
        "history": conversation_history
    }

    def echo(audio):
        messages=[]
        state = sessions[session_id]
        interrupt_flag = state["interrupt_flag"]
        conversation_history = state["history"]

        # 🚨 Stop previous stream (only this session)
        interrupt_flag.set()
        interrupt_flag.clear()

        transcript = whisper_model.stt(audio)
        logger.debug(f"[{session_id}] 🎤 Transcript: {transcript}")

        if not transcript or len(transcript.strip()) < 2:
            return

        response = chat_instance.stream_chat(transcript, conversation_history)

        content_to_stream = ""
        full_response = ""

        messages.append({
            "role": "user",
            "content": transcript
        })

        for chunk in response:
            if interrupt_flag.is_set():
                logger.debug(f"[{session_id}] ⛔ LLM interrupted")
                return


            if chunk:
                response_text = chunk

                # ✅ Your original chunk logic (unchanged)
                if response_text and response_text[-1] not in [".", "!", "?", ","]:
                    content_to_stream += response_text
                    full_response += response_text
                else:
                    content_to_stream += response_text
                    full_response += response_text

                    logger.debug(f"[{session_id}] 🤖 Response: {content_to_stream}")

                    for audio_chunk in tts_model.stream_tts_sync(content_to_stream):
                        if interrupt_flag.is_set():
                            logger.debug(f"[{session_id}] ⛔ TTS interrupted")
                            return
                        yield audio_chunk

                    content_to_stream = ""
        
        messages.append({
            "role": "assistant",
            "content": full_response
        })

        yield AdditionalOutputs(messages)

    return Stream(
        ReplyOnPause(echo),
        modality="audio",
        mode="send-receive",
        #additional_inputs=[gr.Textbox(label="User Input", lines=10)],
        additional_outputs=[gr.Chatbot(type="messages")],
        additional_outputs_handler=lambda old, new: new
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Local Voice Chat Advanced")
    parser.add_argument(
        "--phone",
        action="store_true",
        help="Launch with FastRTC phone interface (get a temp phone number)",
    )
    args = parser.parse_args()

    stream = create_stream(agent)

    if args.phone:
        logger.info("Launching with FastRTC phone interface...")
        stream.fastphone()
    else:
        logger.info("Launching with Gradio UI...")
        stream.ui.launch(share=True)