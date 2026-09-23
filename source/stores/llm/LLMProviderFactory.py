from .LLMEnums import LLMEnums
from .providers import OpenAIProvider, LocalProvider

class LLMProviderFactory:

    def __init__(self, config):
        self.config = config

    def create(self, provider: str):
        provider = (provider or "").upper()

        if provider == LLMEnums.OPENAI.value:
            if not self.config.OPENAI_API_KEY or self.config.OPENAI_API_KEY.strip() in ("", "sk-"):
                raise ValueError("OPENAI_API_KEY is not set in source/.env.")
            return OpenAIProvider(
                api_key=self.config.OPENAI_API_KEY,
                api_url=self.config.OPENAI_API_URL,
                default_input_max_characters=self.config.INPUT_DEFAULT_MAX_CHARACTERS,
                default_generation_max_output_tokens=self.config.GENERATION_DEFAULT_MAX_TOKENS,
                default_generation_temperature=self.config.GENERATION_DEFAULT_TEMPERATURE,
            )

        if provider == LLMEnums.LOCAL.value:
            return LocalProvider()

        raise ValueError(f"Unknown LLM backend: {provider!r}. Use one of: {[e.value for e in LLMEnums]}")
