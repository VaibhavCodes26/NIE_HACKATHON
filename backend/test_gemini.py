import os
import time
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

start = time.perf_counter()

interaction = client.interactions.create(
    model="gemini-3.5-flash-lite",
    input="Reply with exactly: NammaPrayana AI is ready.",
)

elapsed = time.perf_counter() - start

print("\nGemini response:")
print(interaction.output_text)
print(f"\n[Time] Total time: {elapsed:.2f} seconds")