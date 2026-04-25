def get_llm(provider: str | None = None, **kwargs):
    """Return a LangChain chat model for the given provider."""
    from django.conf import settings

    provider = provider or settings.LLM_PROVIDER

    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=settings.OPENAI_MODEL,
            api_key=settings.OPENAI_API_KEY,
            **kwargs,
        )

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=settings.ANTHROPIC_MODEL,
            api_key=settings.ANTHROPIC_API_KEY,
            **kwargs,
        )

    if provider == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=settings.OLLAMA_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
            **kwargs,
        )

    raise ValueError(
        f"Unknown LLM provider '{provider}'. "
        "Set LLM_PROVIDER to openai, anthropic, or ollama."
    )
