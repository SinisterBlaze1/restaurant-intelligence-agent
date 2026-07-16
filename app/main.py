from app.ai_search import extract_filters
from pydantic import BaseModel

class NLQuery(BaseModel):
    query: str

from fastapi import FastAPI, Query
from sqlalchemy import text
from app.database import engine

app = FastAPI(title="Restaurant Intelligence API")

@app.get("/")
def root():
    return {"message": "Restaurant Intelligence API is running"}


@app.get("/restaurants")
def get_restaurants(limit: int = 20):
    query = text("""
    SELECT DISTINCT ON (name, location)
        name, location, cuisines, rate, approx_cost, votes, online_order
        FROM (
            SELECT DISTINCT ON (name, location)
                name, location, cuisines, rate, approx_cost, votes, online_order
            FROM restaurants
            WHERE rate IS NOT NULL
            ORDER BY name, location, votes DESC, rate DESC NULLS LAST
        ) deduped
        ORDER BY name, location,rate DESC,votes DESC
        LIMIT :limit
    """)
    with engine.connect() as conn:
        result = conn.execute(query, {"limit": limit})
        rows = result.mappings().all()
    return [dict(row) for row in rows]


@app.get("/search")
def search_restaurants(
    cuisine: str = Query(None),
    min_rating: float = Query(3.5),
    max_cost: int = Query(1000),
    location: str = Query(None),
    online_order: bool = Query(None),
    limit: int = Query(20)
):
    filters = ["rate >= :min_rating", "approx_cost <= :max_cost"]
    params = {"min_rating": min_rating, "max_cost": max_cost, "limit": limit}

    if cuisine:
        filters.append("cuisines ILIKE :cuisine")
        params["cuisine"] = f"%{cuisine}%"

    if location:
        filters.append("location ILIKE :location")
        params["location"] = f"%{location}%"

    if online_order is not None:
        filters.append("online_order = :online_order")
        params["online_order"] = online_order

    where_clause = " AND ".join(filters)

    query = text(f"""
    SELECT DISTINCT ON (name, location)
         name, location, cuisines, rate, approx_cost, votes, online_order, book_table
        FROM (
            SELECT DISTINCT ON (name, location)
                name, location, cuisines, rate, approx_cost, votes, online_order, book_table
            FROM restaurants
            WHERE {where_clause}
            ORDER BY name, location, votes DESC, rate DESC NULLS LAST
        ) deduped
        ORDER BY name, location, rate DESC, votes DESC
        LIMIT :limit
    """)

    with engine.connect() as conn:
        result = conn.execute(query, params)
        rows = result.mappings().all()
    return [dict(row) for row in rows]


@app.get("/insights")
def get_insights():
    query = text("""
        SELECT 
            COUNT(*) as total_restaurants,
            ROUND(AVG(rate)::numeric, 2) as avg_rating,
            ROUND(AVG(approx_cost)::numeric, 0) as avg_cost,
            SUM(CASE WHEN online_order = true THEN 1 ELSE 0 END) as online_order_count
        FROM restaurants
        WHERE rate IS NOT NULL
    """)
    with engine.connect() as conn:
        result = conn.execute(query)
        row = result.mappings().first()
    return dict(row)


@app.get("/top-locations")
def top_locations():
    query = text("""
        SELECT 
            location,
            COUNT(*) as total,
            ROUND(AVG(rate)::numeric, 2) as avg_rating,
            ROUND(AVG(approx_cost)::numeric, 0) as avg_cost
        FROM restaurants
        WHERE rate IS NOT NULL AND location IS NOT NULL
        GROUP BY location
        ORDER BY avg_rating DESC
        LIMIT 10
    """)
    with engine.connect() as conn:
        result = conn.execute(query)
        rows = result.mappings().all()
    return [dict(row) for row in rows]

@app.post("/api/ai-search") # Or whatever your exact decorator route is right above it
def ai_search(body: NLQuery):
    filters = extract_filters(body.query)

    params = {
        "min_rating": filters.get("min_rating") or 3.5,
        "max_cost": filters.get("max_cost") or 2000,
        "limit": 10
    }
    
    if filters.get("cuisine"):
        params["cuisine"] = filters["cuisine"]
    if filters.get("location"):
        params["location"] = filters["location"]
    if filters.get("online_order") is not None:
        params["online_order"] = filters["online_order"]

    cuisine_filter = "AND cuisines ILIKE :cuisine" if params.get("cuisine") else ""
    location_filter = "AND location ILIKE :location" if params.get("location") else ""
    online_filter = "AND online_order = :online_order" if params.get("online_order") is not None else ""

    query = text(f"""
    SELECT DISTINCT ON (name, location)
         name, location, cuisines, rate, approx_cost, votes, online_order
        FROM restaurants
        WHERE rate IS NOT NULL 
          AND approx_cost IS NOT NULL
          AND rate >= :min_rating
          AND approx_cost <= :max_cost
          {cuisine_filter}
          {location_filter}
          {online_filter}
        ORDER BY name, location, rate DESC, votes DESC
        LIMIT :limit
    """)

    with engine.connect() as conn:
        result = conn.execute(query, params)
        rows = result.mappings().all()

    return {
        "query": body.query,
        "filters_extracted": filters,
        "results": [dict(row) for row in rows]
    }