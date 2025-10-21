"""LLM Provider Registry for managing multiple LLM providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

import httpx

from backend.config.settings import settings


@dataclass
class LLMModel:
    """LLM model metadata."""
    id: str
    name: str
    provider: str
    context_window: int
    max_output_tokens: int
    supports_streaming: bool
    cost_per_1k_input_tokens: float
    cost_per_1k_output_tokens: float
    description: Optional[str] = None


@dataclass
class LLMProvider:
    """LLM provider metadata."""
    id: str
    name: str
    display_name: str
    description: str
    requires_api_key: bool
    supports_streaming: bool
    base_url: str
    models: List[LLMModel]


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    async def generate(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 600,
        **kwargs,
    ) -> Dict[str, Any]:
        """Generate response from LLM.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model identifier
            temperature: Sampling temperature
            max_tokens: Maximum output tokens
            **kwargs: Provider-specific parameters

        Returns:
            Response dict with 'text' and 'tokens' keys
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the client connection."""
        pass


class SarvamLLMClient(BaseLLMClient):
    """Sarvam AI LLM client."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self.api_key = api_key or settings.sarvam_api_key
        self.base_url = base_url or str(settings.sarvam_api_base)
        self._client = client or httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(30.0, connect=10.0),
        )

    async def generate(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 600,
        **kwargs,
    ) -> Dict[str, Any]:
        """Generate response from Sarvam LLM."""
        headers = {
            "api-subscription-key": self.api_key,
            "Content-Type": "application/json",
        }

        payload = {
            "messages": messages,
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        response = await self._client.post(
            "/v1/chat/completions",
            json=payload,
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()

        # Extract text and token usage
        text = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})

        return {
            "text": text,
            "tokens": {
                "prompt": usage.get("prompt_tokens", 0),
                "completion": usage.get("completion_tokens", 0),
                "total": usage.get("total_tokens", 0),
            },
        }

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()


class OpenAILLMClient(BaseLLMClient):
    """OpenAI LLM client."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self.api_key = api_key or settings.openai_api_key
        if not self.api_key:
            raise ValueError("OpenAI API key not configured")

        self._client = client or httpx.AsyncClient(
            base_url="https://api.openai.com/v1",
            timeout=httpx.Timeout(60.0, connect=10.0),
        )

    async def generate(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 600,
        **kwargs,
    ) -> Dict[str, Any]:
        """Generate response from OpenAI."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        response = await self._client.post(
            "/chat/completions",
            json=payload,
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()

        text = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})

        return {
            "text": text,
            "tokens": {
                "prompt": usage.get("prompt_tokens", 0),
                "completion": usage.get("completion_tokens", 0),
                "total": usage.get("total_tokens", 0),
            },
        }

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()


class AnthropicLLMClient(BaseLLMClient):
    """Anthropic (Claude) LLM client."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self.api_key = api_key or getattr(settings, "anthropic_api_key", None)
        if not self.api_key:
            raise ValueError("Anthropic API key not configured")

        self._client = client or httpx.AsyncClient(
            base_url="https://api.anthropic.com/v1",
            timeout=httpx.Timeout(60.0, connect=10.0),
        )

    async def generate(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 600,
        **kwargs,
    ) -> Dict[str, Any]:
        """Generate response from Anthropic Claude."""
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

        # Extract system message if present
        system_message = None
        filtered_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                filtered_messages.append(msg)

        payload = {
            "model": model,
            "messages": filtered_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if system_message:
            payload["system"] = system_message

        response = await self._client.post(
            "/messages",
            json=payload,
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()

        text = data["content"][0]["text"]
        usage = data.get("usage", {})

        return {
            "text": text,
            "tokens": {
                "prompt": usage.get("input_tokens", 0),
                "completion": usage.get("output_tokens", 0),
                "total": usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
            },
        }

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()


class LLMProviderRegistry:
    """Registry for LLM providers and models."""

    _instance: Optional["LLMProviderRegistry"] = None
    _providers: Dict[str, LLMProvider] = {}
    _clients: Dict[str, type[BaseLLMClient]] = {}

    def __new__(cls) -> "LLMProviderRegistry":
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        """Initialize providers and register default providers."""
        # Register Sarvam provider
        self.register_provider(
            LLMProvider(
                id="sarvam",
                name="sarvam",
                display_name="Sarvam AI",
                description="Indian language specialist with multilingual support",
                requires_api_key=True,
                supports_streaming=True,
                base_url=str(settings.sarvam_api_base),
                models=[
                    LLMModel(
                        id="sarvam-1",
                        name="Sarvam-1",
                        provider="sarvam",
                        context_window=8192,
                        max_output_tokens=2048,
                        supports_streaming=True,
                        cost_per_1k_input_tokens=0.0001,
                        cost_per_1k_output_tokens=0.0002,
                        description="Sarvam's flagship model optimized for Indian languages",
                    ),
                ],
            ),
            SarvamLLMClient,
        )

        # Register OpenAI provider
        self.register_provider(
            LLMProvider(
                id="openai",
                name="openai",
                display_name="OpenAI",
                description="Industry-leading models from OpenAI",
                requires_api_key=True,
                supports_streaming=True,
                base_url="https://api.openai.com/v1",
                models=[
                    LLMModel(
                        id="gpt-3.5-turbo",
                        name="GPT-3.5 Turbo",
                        provider="openai",
                        context_window=16385,
                        max_output_tokens=4096,
                        supports_streaming=True,
                        cost_per_1k_input_tokens=0.0005,
                        cost_per_1k_output_tokens=0.0015,
                        description="Fast and cost-effective",
                    ),
                    LLMModel(
                        id="gpt-4",
                        name="GPT-4",
                        provider="openai",
                        context_window=8192,
                        max_output_tokens=8192,
                        supports_streaming=True,
                        cost_per_1k_input_tokens=0.03,
                        cost_per_1k_output_tokens=0.06,
                        description="Most capable model",
                    ),
                    LLMModel(
                        id="gpt-4-turbo",
                        name="GPT-4 Turbo",
                        provider="openai",
                        context_window=128000,
                        max_output_tokens=4096,
                        supports_streaming=True,
                        cost_per_1k_input_tokens=0.01,
                        cost_per_1k_output_tokens=0.03,
                        description="Latest GPT-4 with large context",
                    ),
                ],
            ),
            OpenAILLMClient,
        )

        # Register Anthropic provider
        self.register_provider(
            LLMProvider(
                id="anthropic",
                name="anthropic",
                display_name="Anthropic (Claude)",
                description="Claude models from Anthropic",
                requires_api_key=True,
                supports_streaming=True,
                base_url="https://api.anthropic.com/v1",
                models=[
                    LLMModel(
                        id="claude-3-haiku-20240307",
                        name="Claude 3 Haiku",
                        provider="anthropic",
                        context_window=200000,
                        max_output_tokens=4096,
                        supports_streaming=True,
                        cost_per_1k_input_tokens=0.00025,
                        cost_per_1k_output_tokens=0.00125,
                        description="Fastest and most compact model",
                    ),
                    LLMModel(
                        id="claude-3-sonnet-20240229",
                        name="Claude 3 Sonnet",
                        provider="anthropic",
                        context_window=200000,
                        max_output_tokens=4096,
                        supports_streaming=True,
                        cost_per_1k_input_tokens=0.003,
                        cost_per_1k_output_tokens=0.015,
                        description="Balanced performance and speed",
                    ),
                    LLMModel(
                        id="claude-3-opus-20240229",
                        name="Claude 3 Opus",
                        provider="anthropic",
                        context_window=200000,
                        max_output_tokens=4096,
                        supports_streaming=True,
                        cost_per_1k_input_tokens=0.015,
                        cost_per_1k_output_tokens=0.075,
                        description="Most powerful Claude model",
                    ),
                ],
            ),
            AnthropicLLMClient,
        )

    def register_provider(
        self,
        provider: LLMProvider,
        client_class: type[BaseLLMClient],
    ) -> None:
        """Register an LLM provider.

        Args:
            provider: Provider metadata
            client_class: Client class for the provider
        """
        self._providers[provider.id] = provider
        self._clients[provider.id] = client_class

    def get_provider(self, provider_id: str) -> Optional[LLMProvider]:
        """Get provider by ID.

        Args:
            provider_id: Provider identifier

        Returns:
            LLMProvider or None if not found
        """
        return self._providers.get(provider_id)

    def list_providers(self) -> List[LLMProvider]:
        """List all registered providers.

        Returns:
            List of LLMProvider objects
        """
        return list(self._providers.values())

    def get_models(self, provider_id: str) -> List[LLMModel]:
        """Get models for a provider.

        Args:
            provider_id: Provider identifier

        Returns:
            List of LLMModel objects
        """
        provider = self._providers.get(provider_id)
        if not provider:
            return []
        return provider.models

    def get_model(self, provider_id: str, model_id: str) -> Optional[LLMModel]:
        """Get specific model.

        Args:
            provider_id: Provider identifier
            model_id: Model identifier

        Returns:
            LLMModel or None if not found
        """
        models = self.get_models(provider_id)
        for model in models:
            if model.id == model_id:
                return model
        return None

    def create_client(
        self,
        provider_id: str,
        api_key: Optional[str] = None,
    ) -> BaseLLMClient:
        """Create a client instance for a provider.

        Args:
            provider_id: Provider identifier
            api_key: Optional API key override

        Returns:
            BaseLLMClient instance

        Raises:
            ValueError: If provider not found or not supported
        """
        if provider_id not in self._clients:
            raise ValueError(f"Provider '{provider_id}' not found")

        client_class = self._clients[provider_id]

        # Create client with optional API key
        if api_key:
            return client_class(api_key=api_key)
        else:
            return client_class()


__all__ = [
    "LLMModel",
    "LLMProvider",
    "BaseLLMClient",
    "SarvamLLMClient",
    "OpenAILLMClient",
    "AnthropicLLMClient",
    "LLMProviderRegistry",
]
