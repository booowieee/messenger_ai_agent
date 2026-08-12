import asyncio
from google import genai
from src.config import settings

client = genai.Client(api_key=settings.GEMINI_API_KEY)


async def main():
    print("Listing available models for the API key...")
    try:
        # List models
        response = client.models.list()
        for m in response:
            print(f"- {m.name} (Supported actions: {m.supported_generation_methods})")
    except Exception as e:
        print(f"Error listing models: {e}")


if __name__ == "__main__":
    asyncio.run(main())
