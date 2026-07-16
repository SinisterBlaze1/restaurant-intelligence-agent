from app.ai_search import extract_filters

queries = [
    "I want good North Indian food under 800 rupees in Koramangala",
    "Best biryani in Indiranagar, budget around 600",
    "Cheap Chinese food with online ordering, not too far from Whitefield",
    "Top rated Italian restaurant, doesn't matter about price"
]

for q in queries:
    print(f"\nQuery: {q}")
    print(f"Filters: {extract_filters(q)}")