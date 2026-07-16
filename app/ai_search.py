import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SYSTEM_PROMPT = """You are a restaurant search assistant.
Extract search filters from the user's natural language query.

Return ONLY a JSON object with these exact fields:
{
    "cuisine": "cuisine type or null",
    "location": "area name or null",
    "max_cost": number or null,
    "min_rating": number or null,
    "online_order": true/false/null
}

Rules:
- cuisine: extract food type (North Indian, Chinese, Italian etc). null if not mentioned.
- location: extract Bangalore area name only (Koramangala, Indiranagar etc). null if not mentioned.
- max_cost: extract budget as integer, total for two people. null if not mentioned.
- min_rating: default 3.5 if not mentioned. Use 4.0 if user says best/top rated/highly rated.
- online_order: true only if user mentions delivery or online order. null otherwise.

Return ONLY the JSON object. No explanation. No markdown. No code blocks."""


def extract_filters(user_query: str) -> dict:
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_query}
        ],
        temperature=0,
        max_tokens=150
    )

    raw = response.choices[0].message.content.strip()

    # Strip markdown code blocks if model adds them anyway
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        filters = json.loads(raw)
        return filters
    except json.JSONDecodeError:
        return {
            "cuisine": None,
            "location": None,
            "max_cost": 1000,
            "min_rating": 3.5,
            "online_order": None
        }