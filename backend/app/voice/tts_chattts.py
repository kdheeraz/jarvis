from typing import Generator

import numpy as np
from loguru import logger


class ChatTTSModel:
    """ChatTTS (2Noise/ChatTTS) wrapper that yields FastRTC-compatible audio tuples.

    ChatTTS emits 24kHz float32; we convert to int16 (1, N) for FastRTC.
    Also translates the LLM-side `<laugh>`/`<sigh>`/etc. tags into the
    bracket tokens (`[laugh]`, `[break]`) ChatTTS understands natively.
    """

    _TAG_MAP = {
        "<laugh>": "[laugh]",
        "<chuckle>": "[laugh]",
        "<sigh>": "[break]",
        "<gasp>": "[break]",
        "<cough>": "[break]",
    }

    def __init__(
        self,
        device: str = "cpu",
        compile: bool = False,
        speaker_seed: int = 42,
        temperature: float = 0.3,
        top_p: float = 0.7,
        top_k: int = 20,
        sample_rate: int = 24000,
        refine_text_prompt: str = "[oral_2][laugh_0][break_4]",
    ):
        import ChatTTS
        import torch

        self.chat = ChatTTS.Chat()
        self.chat.load(compile=compile, device=device)

        torch.manual_seed(speaker_seed)
        spk_emb = self.chat.sample_random_speaker()

        self._params_infer = ChatTTS.Chat.InferCodeParams(
            spk_emb=spk_emb,
            temperature=temperature,
            top_P=top_p,
            top_K=top_k,
        )
        self._params_refine = ChatTTS.Chat.RefineTextParams(prompt=refine_text_prompt)
        self.sample_rate = sample_rate
        logger.info(
            f"ChatTTS loaded: device={device} seed={speaker_seed} "
            f"sample_rate={sample_rate}"
        )

    @classmethod
    def _translate_tags(cls, text: str) -> str:
        for src, dst in cls._TAG_MAP.items():
            text = text.replace(src, dst)
        return text

    def stream_tts_sync(self, text: str) -> Generator:
        text = self._translate_tags(text)

        wavs = self.chat.infer(
            [text],
            params_refine_text=self._params_refine,
            params_infer_code=self._params_infer,
            stream=True,
        )

        for chunk in wavs:
            if chunk is None:
                continue
            arr = chunk[0] if isinstance(chunk, (list, tuple)) else chunk
            if arr is None or not isinstance(arr, np.ndarray) or arr.size == 0:
                continue
            audio_int16 = np.clip(arr * 32767.0, -32768, 32767).astype(np.int16)
            yield (self.sample_rate, audio_int16.reshape(1, -1))
