"""Abstract base class + common types for all LLM providers."""

from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    """Abstract LLM provider. Every engine implements this."""

    @abstractmethod
    def generate(self, prompt: str, max_tokens: int = 1500, temperature: float = 0.3) -> str:
        ...

    @abstractmethod
    def is_available(self) -> bool:
        ...

    def get_status(self) -> dict[str, Any]:
        return {
            "type": self.__class__.__name__,
            "available": self.is_available(),
        }


ProviderStatus = dict[str, Any]
