import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv("d:/Paras0218/PdfReader/backendPY/.env")
sys.path.insert(0, "d:/Paras0218/PdfReader/backendPY")

from services.llm_service import GroqAdapter
from domain.value_objects.llm import LLMSettings

async def test_groq_adapter():
    adapter = GroqAdapter()
    settings = LLMSettings(temperature=0.1, max_tokens=150, timeout=15.0)
    prompt = "System Prompt:\nYou are an intelligent document assistant.\n\nUser Message:\nWhat is a Sample PDF?"
    print("Testing GroqAdapter streaming...")
    async for chunk in adapter.generate_stream(prompt, settings, "openai/gpt-oss-120b"):
        print(chunk.content, end="", flush=True)
    print("\n\nGROQ ADAPTER STREAM TEST PASSED!")

if __name__ == "__main__":
    asyncio.run(test_groq_adapter())
