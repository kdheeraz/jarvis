from langchain_core.language_models import BaseChatModel
from loguru import logger

from app.config import JarvisConfig, get_config


def create_llm(config: JarvisConfig | None = None) -> BaseChatModel:
    """Create a LangChain ChatModel based on the active provider config."""
    if config is None:
        config = get_config()

    provider = config.llm.provider
    logger.info(f"Creating LLM with provider: {provider}")

    if provider == "ollama":
        return _create_ollama(config)
    elif provider == "openai":
        return _create_openai(config)
    elif provider == "anthropic":
        return _create_anthropic(config)
    elif provider == "bedrock":
        return _create_bedrock(config)
    elif provider == "groq":
        return _create_groq(config)
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


def _create_ollama(config: JarvisConfig) -> BaseChatModel:
    from langchain_ollama import ChatOllama

    cfg = config.llm.ollama
    return ChatOllama(
        model=cfg.model,
        reasoning=cfg.reasoning,
        base_url=cfg.base_url,
        temperature=cfg.temperature,
    )


def _create_openai(config: JarvisConfig) -> BaseChatModel:
    from langchain_openai import ChatOpenAI

    cfg = config.llm.openai
    return ChatOpenAI(
        model=cfg.model,
        api_key=cfg.api_key,
        temperature=cfg.temperature,
    )


def _create_anthropic(config: JarvisConfig) -> BaseChatModel:
    from langchain_anthropic import ChatAnthropic

    cfg = config.llm.anthropic
    return ChatAnthropic(
        model=cfg.model,
        api_key=cfg.api_key,
        temperature=cfg.temperature,
    )


def _create_bedrock(config: JarvisConfig) -> BaseChatModel:
    from langchain_aws import ChatBedrock

    cfg = config.llm.bedrock
    return ChatBedrock(
        model_id=cfg.model_id,
        region_name=cfg.region,
        model_kwargs={"temperature": cfg.temperature},
    )


def _create_groq(config: JarvisConfig) -> BaseChatModel:
    import os

    from langchain_groq import ChatGroq

    cfg = config.llm.groq
    api_key = cfg.api_key or os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        raise RuntimeError("Groq LLM requires GROQ_API_KEY (env or config).")
    return ChatGroq(
        model=cfg.model,
        api_key=api_key,
        temperature=cfg.temperature,
    )
