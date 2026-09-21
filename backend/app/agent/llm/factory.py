from app.agent.llm.base import LLMProvider


def get_llm_provider(provider_name: str) -> LLMProvider:
    if provider_name == "test":
        from app.agent.llm.test_provider import ScriptedTestProvider

        return ScriptedTestProvider()
    if provider_name == "ollama":
        from app.agent.llm.ollama_provider import OllamaProvider

        return OllamaProvider()
    raise ValueError(f"Unknown LLM provider: {provider_name}")
