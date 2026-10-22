
import json
import os

from dotenv import load_dotenv
from google import genai

load_dotenv()

MODEL_NAME = "gemini-3.5-flash-lite"


def generate_itinerary(
    *,
    destinations: list[str],
    start_date: str,
    end_date: str,
    traveller_count: int,
    travel_style: str,
    total_budget: int,
    interests: list[str],
) -> dict:
    """Generate a structured Karnataka itinerary using Gemini."""

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured.")

    client = genai.Client(api_key=api_key)

    prompt = f"""
You are the itinerary-planning AI for NammaPrayana,
a Karnataka tourism application.

Create a practical itinerary using the user's preferences.

Trip details:
- Destinations: {json.dumps(destinations)}
- Start date: {start_date}
- End date: {end_date}
- Travellers: {traveller_count}
- Travel style: {travel_style}
- Total budget in INR: {total_budget}
- Interests: {json.dumps(interests)}

Rules:
- Return only valid JSON. No Markdown fences.
- Do not invent confirmed transport schedules, hotel availability,
  live prices, opening hours, or weather forecasts.
- Do not claim that bookings have been made.
- Keep the itinerary concise and realistic.
- Consider the budget and travel time between destinations.
- Clearly label estimates and information requiring verification.
- Use this exact JSON structure:
{{
  "title": "Trip title",
  "days": [
    {{
      "day_number": 1,
      "date": "YYYY-MM-DD",
      "destination": "Destination name",
      "activities": [
        {{
          "time": "Morning",
          "name": "Activity name",
          "description": "Short description"
        }}
      ]
    }}
  ],
  "budget_note": "Short budget explanation",
  "verification_note": "Information the traveller should verify"
}}
"""

    interaction = client.interactions.create(
        model=MODEL_NAME,
        input=prompt,
    )

    output = interaction.output_text
    if not output:
        raise RuntimeError("Gemini returned an empty response.")

    # Remove optional Markdown fences if the model includes them.
    cleaned = output.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

    result = json.loads(cleaned)

    if not isinstance(result, dict) or not isinstance(
        result.get("days"), list
    ):
        raise ValueError("Gemini returned an unexpected itinerary format.")

    return result
