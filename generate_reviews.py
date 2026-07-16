import pandas as pd
from sqlalchemy import create_engine, text
from groq import Groq
import os
import json
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(dotenv_path=Path(__file__).parent / ".env")
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

engine = create_engine(
    'postgresql://postgres:12345678@localhost:5432/restaurant_db'
)

# Get top 200 restaurants by votes
with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT DISTINCT ON (name) name, cuisines, rate, approx_cost, location
        FROM restaurants
        WHERE rate IS NOT NULL
        ORDER BY name, votes DESC
        LIMIT 200
    """))
    restaurants = [dict(r) for r in result.mappings().all()]

print(f"Generating reviews for {len(restaurants)} restaurants...")

all_reviews = []

for i, r in enumerate(restaurants):
    prompt = f"""Generate 3 short realistic customer reviews for this restaurant:
Name: {r['name']}
Cuisine: {r['cuisines']}
Rating: {r['rate']}/5
Cost for two: Rs {r['approx_cost']}
Location: {r['location']}

Return ONLY a JSON array of 3 strings. Each review should be 1-2 sentences.
Reflect the rating honestly — high ratings get positive reviews, low ratings get mixed ones.
No markdown, no explanation, just the JSON array."""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=300
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()
        reviews = json.loads(raw)
        for review in reviews:
            all_reviews.append({
                "restaurant_name": r["name"],
                "review_text": review,
                "rating": r["rate"]
            })
        if i % 20 == 0:
            print(f"Done {i+1}/{len(restaurants)}")
    except Exception as e:
        print(f"Skipped {r['name']}: {e}")
        continue

reviews_df = pd.DataFrame(all_reviews)
reviews_df.to_sql("reviews", engine, if_exists="replace", index=False)
print(f"Done. {len(reviews_df)} reviews saved to database.")