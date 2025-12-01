import pytest
from pydantic import BaseModel
from uroboros.llm.client import LLMClient

class TestSchema(BaseModel):
    greeting: str
    confidence: float

@pytest.mark.asyncio
async def test_llm_structured_output_compatibility():
    """
    Integration Test: Verifies that the configured model actually supports
    Structured Outputs (json_schema).
    
    If this fails, it means the model in .env (e.g. gpt-4-turbo) 
    is too old for the strict parsing logic we use.
    """
    client = LLMClient()
    
    print(f"\nTesting connectivity with model: {client.model}")
    
    try:
        response = await client.chat_structured(
            system_prompt="You are a test system.",
            user_prompt="Say hello and give a confidence score of 1.0",
            response_model=TestSchema
        )
        
        assert response.greeting is not None
        assert response.confidence == 1.0
        print("✅ Model supports Structured Outputs.")
        
    except Exception as e:
        pytest.fail(f"Model '{client.model}' failed compatibility check: {str(e)}")