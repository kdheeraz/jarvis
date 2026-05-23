import os
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field


class AppConfig(BaseModel):
    name: str = "Jarvis"
    theme: str = "#3b82f6"  # Primary brand color (hex). Drives UI accents like the voice orb.
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]


class AuthConfig(BaseModel):
    enabled: bool = False
    jwt_secret_key: str = "change-me-in-production"
    jwt_expiry_minutes: int = 1440
    admin_username: str = "admin"
    admin_password: str = "admin"


class OllamaConfig(BaseModel):
    model: str = "qwen2.5:3b"
    base_url: str = "http://ollama:11434"
    temperature: float = 0.7
    reasoning: bool = False


class OpenAIConfig(BaseModel):
    model: str = "gpt-4o"
    api_key: str = ""
    temperature: float = 0.7
    reasoning: bool = False


class AnthropicConfig(BaseModel):
    model: str = "claude-sonnet-4-20250514"
    api_key: str = ""
    temperature: float = 0.7
    reasoning: bool = False


class BedrockConfig(BaseModel):
    model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0"
    region: str = "us-east-1"
    temperature: float = 0.7
    reasoning: bool = False


class GroqLLMConfig(BaseModel):
    model: str = "llama-3.3-70b-versatile"
    api_key: str = ""
    temperature: float = 0.7
    reasoning: bool = False


class LLMConfig(BaseModel):
    provider: str = "ollama"
    system_prompt: str = "You are Jarvis, a helpful AI assistant. Be concise, accurate, and helpful."
    ollama: OllamaConfig = OllamaConfig()
    openai: OpenAIConfig = OpenAIConfig()
    anthropic: AnthropicConfig = AnthropicConfig()
    bedrock: BedrockConfig = BedrockConfig()
    groq: GroqLLMConfig = GroqLLMConfig()


class ChromaDBConfig(BaseModel):
    host: str = "chromadb"
    port: int = 8000


class FAISSConfig(BaseModel):
    index_path: str = "./data/faiss_index"


class OpenSearchConfig(BaseModel):
    host: str = "opensearch"
    port: int = 9200


class PGVectorConfig(BaseModel):
    connection_string: str = "postgresql://jarvis:jarvis@postgres:5432/jarvis"


class RAGConfig(BaseModel):
    enabled: bool = False
    store: str = "chromadb"
    embedding_model: str = "all-MiniLM-L6-v2"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    chromadb: ChromaDBConfig = ChromaDBConfig()
    faiss: FAISSConfig = FAISSConfig()
    opensearch: OpenSearchConfig = OpenSearchConfig()
    pgvector: PGVectorConfig = PGVectorConfig()


class PiperConfig(BaseModel):
    model_path: str = "./models/jarvis-high.onnx"
    config_path: str = "./models/en.json"


class EdgeTTSConfig(BaseModel):
    voice: str = "en-US-AriaNeural"
    rate: str = "+0%"
    pitch: str = "+0Hz"


class KokoroConfig(BaseModel):
    voice: str = "am_michael"
    speed: float = 1.0
    lang: str = "en-us"


class GroqTTSConfig(BaseModel):
    voice: str = "Calum-PlayAI"
    model: str = "playai-tts"
    base_url: str = "https://api.groq.com/openai/v1"
    api_key_env: str = "GROQ_API_KEY"


class ChatTTSConfig(BaseModel):
    """Local ChatTTS (2Noise/ChatTTS) — expressive dialogue TTS with inline
    emotion tokens like [laugh], [break], [uv_break], [lbreak]."""
    device: str = "cpu"          # "cpu" | "cuda" | "mps"
    compile: bool = False        # torch.compile first-run warmup, GPU-only
    speaker_seed: int = 42       # deterministic speaker embedding
    temperature: float = 0.3
    top_p: float = 0.7
    top_k: int = 20
    sample_rate: int = 24000     # ChatTTS emits 24kHz float32
    refine_text_prompt: str = "[oral_2][laugh_0][break_4]"


class EmotionTagsConfig(BaseModel):
    """LLM-side instruction that teaches the model to emit inline emotion tags
    (e.g. <laugh>, <sigh>) for expressive TTS backends like Orpheus or
    ChatTTS. Disable for TTS backends that would speak the tags literally
    (Piper, Edge, Kokoro)."""
    enabled: bool = False
    allowed_tags: list[str] = ["<laugh>", "<chuckle>", "<sigh>", "<gasp>", "<cough>"]
    instruction_template: str = (
        "When it genuinely fits the emotional tone, you may sprinkle at most "
        "one or two of these inline cues between sentences: {tags}. "
        "Place them as standalone tokens, never inside a word. "
        "Skip them entirely if the reply is short, factual, or neutral."
    )


class FasterWhisperConfig(BaseModel):
    model_size: str = "small.en"
    device: str = "cpu"
    compute_type: str = "int8"
    beam_size: int = 1
    vad_filter: bool = False
    language: str | None = "en"


class VoiceConfig(BaseModel):
    enabled: bool = True
    stt_model: str = "distil-whisper"
    tts_model: str = "piper"
    piper: PiperConfig = PiperConfig()
    edge: EdgeTTSConfig = EdgeTTSConfig()
    kokoro: KokoroConfig = KokoroConfig()
    groq: GroqTTSConfig = GroqTTSConfig()
    chattts: ChatTTSConfig = ChatTTSConfig()
    emotion_tags: EmotionTagsConfig = EmotionTagsConfig()
    faster_whisper: FasterWhisperConfig = FasterWhisperConfig()


class ToolsConfig(BaseModel):
    enabled: list[str] = ["web_search", "datetime_tool", "calculator", "rag_search"]


class DatabaseConfig(BaseModel):
    url: str = "sqlite:///./data/jarvis.db"


class MemoryConfig(BaseModel):
    """Long-term memory backed by Mneme (memory-as-a-service).
    Jarvis recalls relevant facts before answering and stores new ones after.
    api_key/base_url usually come from env (MNEME_API_KEY / MNEME_BASE_URL)."""
    enabled: bool = False
    base_url: str = "http://host.docker.internal:8000"  # Mneme API (host from inside a container)
    api_key: str = ""                                   # Mneme agent-scoped key
    user_id: str = "jarvis"                             # scopes all memories to one user
    recall_limit: int = 5
    recall_mode: str = "vector"                         # vector | hybrid | lexical


class JarvisConfig(BaseModel):
    app: AppConfig = AppConfig()
    auth: AuthConfig = AuthConfig()
    llm: LLMConfig = LLMConfig()
    rag: RAGConfig = RAGConfig()
    voice: VoiceConfig = VoiceConfig()
    tools: ToolsConfig = ToolsConfig()
    database: DatabaseConfig = DatabaseConfig()
    memory: MemoryConfig = MemoryConfig()


def _resolve_env_vars(data: dict) -> dict:
    """Recursively resolve ${ENV_VAR} references in config values."""
    resolved = {}
    for key, value in data.items():
        if isinstance(value, dict):
            resolved[key] = _resolve_env_vars(value)
        elif isinstance(value, str) and value.startswith("${") and value.endswith("}"):
            env_var = value[2:-1]
            resolved[key] = os.environ.get(env_var, "")
        elif isinstance(value, list):
            resolved[key] = [
                os.environ.get(v[2:-1], "") if isinstance(v, str) and v.startswith("${") and v.endswith("}") else v
                for v in value
            ]
        else:
            resolved[key] = value
    return resolved


def _project_root() -> Path:
    """Resolve the project root (parent of backend/)."""
    return Path(__file__).resolve().parent.parent.parent


def load_config(config_path: Optional[str] = None) -> JarvisConfig:
    """Load configuration from YAML file with env var resolution."""
    root = _project_root()

    if config_path is None:
        config_path = os.environ.get("CONFIG_PATH")

    # Load default config
    default_path = root / "config" / "default.yaml"
    config_data = {}

    if default_path.exists():
        with open(default_path) as f:
            config_data = yaml.safe_load(f) or {}

    # Load user config (overrides defaults)
    # Try explicit path first, then project-root-relative
    user_path = None
    if config_path:
        user_path = Path(config_path)
    else:
        candidate = root / "config" / "config.yaml"
        if candidate.exists():
            user_path = candidate

    if user_path and user_path.exists():
        with open(user_path) as f:
            user_data = yaml.safe_load(f) or {}
        config_data = _deep_merge(config_data, user_data)

    # Resolve environment variables
    config_data = _resolve_env_vars(config_data)

    # Override database URL from env if set
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        config_data.setdefault("database", {})["url"] = db_url

    jwt_secret = os.environ.get("JWT_SECRET_KEY")
    if jwt_secret:
        config_data.setdefault("auth", {})["jwt_secret_key"] = jwt_secret

    # Mneme long-term memory (from env)
    if os.environ.get("MNEME_API_KEY"):
        config_data.setdefault("memory", {})["api_key"] = os.environ["MNEME_API_KEY"]
    if os.environ.get("MNEME_BASE_URL"):
        config_data.setdefault("memory", {})["base_url"] = os.environ["MNEME_BASE_URL"]
    if os.environ.get("MNEME_ENABLED"):
        config_data.setdefault("memory", {})["enabled"] = (
            os.environ["MNEME_ENABLED"].lower() in ("1", "true", "yes", "on")
        )

    return JarvisConfig(**config_data)


def save_config(config: JarvisConfig, config_path: Optional[str] = None) -> None:
    """Save configuration to YAML file."""
    if config_path is None:
        config_path = os.environ.get("CONFIG_PATH")
    if config_path is None:
        config_path = str(_project_root() / "config" / "config.yaml")

    path = Path(config_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w") as f:
        yaml.dump(config.model_dump(), f, default_flow_style=False, sort_keys=False)


def _deep_merge(base: dict, override: dict) -> dict:
    """Deep merge two dicts. Override values take precedence."""
    merged = base.copy()
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


# Singleton config instance
_config: Optional[JarvisConfig] = None


def get_config() -> JarvisConfig:
    """Get the singleton config instance."""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def reload_config() -> JarvisConfig:
    """Reload config from disk."""
    global _config
    _config = load_config()
    return _config
