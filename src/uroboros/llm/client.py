import logging
from typing import Type, TypeVar, Optional, List, Union
from openai import AsyncOpenAI, APIError, RateLimitError
from pydantic import BaseModel
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

from uroboros.core.config import get_settings

# Type variable for Pydantic models to allow generic return types
T = TypeVar("T", bound=BaseModel)

logger = logging.getLogger(__name__)
settings = get_settings()

class LLMClient:
    """
    Async wrapper around LLM providers.
    Currently defaults to OpenAI, but designed to be extensible.
    Enforces strict typing and structured outputs.
    """

    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize the client.
        
        Args:
            model_name: Override default model (e.g. use a cheaper model for summarization)
        """
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY.get_secret_value())
        self.model = model_name or settings.ACTOR_MODEL
        self.logger = logger

    @retry(
        retry=retry_if_exception_type((RateLimitError, APIError)),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        stop=stop_after_attempt(5),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    async def chat(
        self, 
        system_prompt: str, 
        user_prompt: str, 
        temperature: float = 0.0
    ) -> str:
        """
        Standard text completion.
        
        Args:
            system_prompt: The persona/instructions (e.g. "You are a Senior Engineer...")
            user_prompt: The specific task input.
            temperature: Creativity (0.0 for code, 0.7 for creative writing).
            
        Returns:
            The raw string response content.
        """
        self.logger.debug(f"Sending request to {self.model} (Temp: {temperature})")
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature
            )
            content = response.choices[0].message.content
            if content is None:
                raise ValueError("LLM returned null content")
            return content
            
        except Exception as e:
            self.logger.error(f"LLM Chat Error: {str(e)}")
            raise

    @retry(
        retry=retry_if_exception_type((RateLimitError, APIError)),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        stop=stop_after_attempt(5),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    async def chat_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: Type[T],
        temperature: float = 0.0
    ) -> T:
        """
        Structured completion that guarantees a Pydantic object response.
        Uses OpenAI's 'response_format' (beta) for strict schema adherence.
        
        Args:
            response_model: The Pydantic class to parse the response into.
            
        Returns:
            Instance of response_model populated with LLM data.
        """
        self.logger.debug(f"Sending structured request to {self.model} -> {response_model.__name__}")

        try:
            response = await self.client.beta.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format=response_model,
                temperature=temperature
            )
            
            parsed_object = response.choices[0].message.parsed
            
            if parsed_object is None:
                # Fallback: Sometimes refusal or strict content policy triggers None
                # In a real system, we might retry or raise a specific error
                raise ValueError(f"LLM failed to parse into {response_model.__name__}")
                
            return parsed_object

        except Exception as e:
            self.logger.error(f"LLM Structured Error: {str(e)}")
            raise
