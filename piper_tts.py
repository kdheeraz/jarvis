import numpy as np
from typing import Generator
from piper.voice import PiperVoice
from fastrtc import Stream, ReplyOnPause

class PiperTTSModel:
    def __init__(self, model_path: str, config_path: str):
        # Load the local model
        self.voice = PiperVoice.load(model_path, config_path)
        self.sample_rate = self.voice.config.sample_rate

    def stream_tts_sync(self, text: str, options=None) -> Generator:
        """
        Synthesizes text and yields FastRTC-compliant audio tuples.
        Correctly accesses Piper's .audio_int16_bytes attribute.
        """
        # Piper yields AudioChunk objects during synthesis
        for chunk_obj in self.voice.synthesize(text):
            # FIX: Use .audio_int16_bytes instead of .audio
            audio_bytes = chunk_obj.audio_int16_bytes 
            
            # Convert raw bytes to 16-bit integer numpy array
            audio_1d = np.frombuffer(audio_bytes, dtype=np.int16)
            
            # Reshape for FastRTC: (channels, samples) -> (1, -1)
            audio_2d = audio_1d.reshape(1, -1)
            
            yield (self.sample_rate, audio_2d)

# Initializing with your local files



