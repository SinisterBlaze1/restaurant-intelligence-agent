import streamlit as st
import pandas as pd
import plotly.express as px
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

# ── DATABASE CONNECTION ─────────────────────────────────
DATABASE_URL = (
    st.secrets.get("NEON_DATABASE_URL", None) if hasattr(st, "secrets") else None
) or os.getenv("NEON_DATABASE_URL") or "postgresql://postgres:12345678@localhost:5432/restaurant_db"

engine = create_engine(DATABASE_URL)

# ── DATABASE FUNCTIONS ──────────────────────────────────
def get_insights():
    query = text("""
        SELECT COUNT(*) as total_restaurants,
            ROUND(AVG(rate)::numeric, 2) as avg_rating,
            ROUND(AVG(approx_cost)::numeric, 0) as avg_cost,
            SUM(CASE WHEN online_order = true THEN 1 ELSE 0 END) as online_order_count
        FROM restaurants WHERE rate IS NOT NULL
    """)
    with engine.connect() as conn:
        return dict(conn.execute(query).mappings().first())

def get_top_locations():
    query = text("""
        SELECT location, COUNT(*) as total,
            ROUND(AVG(rate)::numeric, 2) as avg_rating,
            ROUND(AVG(approx_cost)::numeric, 0) as avg_cost
        FROM restaurants
        WHERE rate IS NOT NULL AND location IS NOT NULL
        GROUP BY location ORDER BY avg_rating DESC LIMIT 10
    """)
    with engine.connect() as conn:
        return [dict(r) for r in conn.execute(query).mappings().all()]

def search_restaurants(cuisine=None, location=None, max_cost=1000,
                       min_rating=3.5, online_order=None, limit=20):
    conditions = ["rate IS NOT NULL", "approx_cost IS NOT NULL",
                  "rate >= :min_rating", "approx_cost <= :max_cost"]
    params = {"min_rating": min_rating, "max_cost": max_cost, "limit": limit}
    if cuisine:
        conditions.append("cuisines ILIKE :cuisine")
        params["cuisine"] = f"%{cuisine}%"
    if location:
        conditions.append("location ILIKE :location")
        params["location"] = f"%{location}%"
    if online_order is not None:
        conditions.append("online_order = :online_order")
        params["online_order"] = online_order
    where_clause = " AND ".join(conditions)
    query = text(f"""
        SELECT name, location, cuisines, rate, approx_cost, votes, online_order, book_table
        FROM (
            SELECT DISTINCT ON (name)
                name, location, cuisines, rate, approx_cost, votes, online_order, book_table
            FROM restaurants WHERE {where_clause}
            ORDER BY name, rate DESC
        ) deduped
        ORDER BY rate DESC, votes DESC LIMIT :limit
    """)
    with engine.connect() as conn:
        return [dict(r) for r in conn.execute(query, params).mappings().all()]

def get_top_restaurants(limit=300):
    query = text("""
        SELECT DISTINCT ON (name, location)
            name, location, cuisines, rate, approx_cost, votes
        FROM restaurants WHERE rate IS NOT NULL
        ORDER BY name, location, votes DESC LIMIT :limit
    """)
    with engine.connect() as conn:
        return [dict(r) for r in conn.execute(query, {"limit": limit}).mappings().all()]

def ai_search(user_query: str):
    try:
        import os, json
        from groq import Groq
        groq_key = (
            st.secrets.get("GROQ_API_KEY", None) if hasattr(st, "secrets") else None
        ) or os.getenv("GROQ_API_KEY")
        client = Groq(api_key=groq_key)
        SYSTEM_PROMPT = """Extract search filters from the user's restaurant query.
Return ONLY a JSON object:
{
    "cuisine": "cuisine type or null",
    "location": "area name or null",
    "max_cost": number or null,
    "min_rating": number or null,
    "online_order": true/false/null
}
Rules: default min_rating to 3.5. Use 4.0 if user says best/top rated.
Return ONLY JSON. No explanation."""
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_query}
            ],
            temperature=0, max_tokens=150
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        filters = json.loads(raw.strip())
        results = search_restaurants(
            cuisine=filters.get("cuisine"),
            location=filters.get("location"),
            max_cost=filters.get("max_cost") or 2000,
            min_rating=filters.get("min_rating") or 3.5,
            limit=10
        )
        return filters, results
    except Exception as e:
        return {}, []

# ── PAGE CONFIG ─────────────────────────────────────────
st.set_page_config(
    page_title="Restaurant Intelligence",
    page_icon="🍽️",
    layout="wide"
)

st.title("🍽️ Restaurant Intelligence Dashboard")
st.caption("Bangalore restaurant data · 51,632 restaurants · Powered by Zomato dataset")

# ── KPI CARDS ───────────────────────────────────────────
st.subheader("Overview")
insights = get_insights()
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Restaurants", f"{insights['total_restaurants']:,}")
col2.metric("Average Rating", f"{insights['avg_rating']} / 5")
col3.metric("Average Cost for Two", f"₹{int(insights['avg_cost'])}")
col4.metric("Online Order Available", f"{insights['online_order_count']:,}")

st.divider()

# ── INSIGHT CARDS ───────────────────────────────────────
st.subheader("Key Findings")
i1, i2, i3, i4 = st.columns(4)
i1.info("📍 **Lavelle Road** has the highest average rating among all Bangalore areas")
i2.info("📱 Restaurants with **online ordering** rate higher on average (3.72 vs 3.66)")
i3.info("💎 **Premium restaurants** (₹1000+) have the highest average ratings")
i4.info("📅 Restaurants with **table booking** get 5.7x more votes on average")

st.divider()

# ── TOP LOCATIONS CHART ─────────────────────────────────
st.subheader("Top 10 Areas by Average Rating")
locations = get_top_locations()
loc_df = pd.DataFrame(locations)
fig1 = px.bar(
    loc_df, x="avg_rating", y="location", orientation="h",
    color="avg_rating", color_continuous_scale="Teal", text="avg_rating",
    labels={"avg_rating": "Avg Rating", "location": "Area"},
)
fig1.update_traces(textposition="outside")
fig1.update_layout(height=400, coloraxis_showscale=False,
                   yaxis=dict(categoryorder="total ascending"))
st.plotly_chart(fig1, use_container_width=True)

st.divider()

# ── SEARCH SECTION ──────────────────────────────────────
st.subheader("🔍 Search Restaurants")
col_a, col_b, col_c, col_d = st.columns(4)
with col_a:
    cuisine_input = st.text_input("Cuisine", placeholder="e.g. Chinese, Italian")
with col_b:
    location_input = st.text_input("Area", placeholder="e.g. Koramangala")
with col_c:
    max_cost = st.slider("Max cost for two (₹)", 200, 3000, 800, step=100)
with col_d:
    min_rating = st.slider("Minimum rating", 1.0, 5.0, 3.5, step=0.1)

online_only = st.checkbox("Online order available")

if st.button("Search", type="primary"):
    results = search_restaurants(
        cuisine=cuisine_input or None,
        location=location_input or None,
        max_cost=max_cost,
        min_rating=min_rating,
        online_order=True if online_only else None,
        limit=50
    )
    if results:
        results_df = pd.DataFrame(results)
        st.success(f"Found {len(results_df)} restaurants")
        st.dataframe(
            results_df[["name", "location", "cuisines", "rate", "approx_cost", "votes"]],
            column_config={
                "rate": st.column_config.ProgressColumn(
                    "Rating", min_value=0, max_value=5, format="%.1f"),
                "approx_cost": st.column_config.NumberColumn(
                    "Cost for Two", format="₹%d"),
            },
            use_container_width=True, hide_index=True
        )
        if len(results_df) > 3:
            st.subheader("Rating distribution in results")
            fig2 = px.histogram(results_df, x="rate", nbins=10,
                                color_discrete_sequence=["#0ea5e9"])
            fig2.update_layout(height=300)
            st.plotly_chart(fig2, use_container_width=True)
    else:
        st.warning("No restaurants found. Try relaxing your filters.")

st.divider()

# ── COST vs RATING SCATTER ──────────────────────────────
st.subheader("Cost vs Rating — Top 300 restaurants by votes")
top_df = pd.DataFrame(get_top_restaurants(300))
if not top_df.empty and "rate" in top_df.columns:
    fig3 = px.scatter(
        top_df, x="approx_cost", y="rate",
        hover_name="name", hover_data=["location", "votes"],
        color="rate", color_continuous_scale="RdYlGn",
        labels={"approx_cost": "Cost for Two (₹)", "rate": "Rating"},
        size="votes", size_max=25
    )
    fig3.update_layout(height=450, coloraxis_showscale=False)
    st.plotly_chart(fig3, use_container_width=True)

st.divider()

# ── AI SEARCH ───────────────────────────────────────────
st.subheader("🤖 Ask in Plain English")
st.caption("Describe what you want — AI figures out the filters")

nl_query = st.text_input(
    "What are you looking for?",
    placeholder="e.g. Best biryani under ₹600 near Indiranagar with online ordering"
)

if st.button("Ask AI", type="primary"):
    if nl_query.strip():
        with st.spinner("Thinking..."):
            filters, results = ai_search(nl_query)
        if filters:
            st.markdown("**Filters extracted by AI:**")
            fcol1, fcol2, fcol3, fcol4 = st.columns(4)
            fcol1.metric("Cuisine", filters.get("cuisine") or "Any")
            fcol2.metric("Area", filters.get("location") or "Any")
            fcol3.metric("Max Cost", f"₹{filters.get('max_cost') or 2000}")
            fcol4.metric("Min Rating", filters.get("min_rating") or 3.5)
        if results:
            st.success(f"Found {len(results)} restaurants")
            ai_df = pd.DataFrame(results)
            st.dataframe(
                ai_df[["name", "location", "cuisines", "rate", "approx_cost", "votes"]],
                column_config={
                    "rate": st.column_config.ProgressColumn(
                        "Rating", min_value=0, max_value=5, format="%.1f"),
                    "approx_cost": st.column_config.NumberColumn(
                        "Cost for Two", format="₹%d"),
                },
                use_container_width=True, hide_index=True
            )
        else:
            st.warning("No results found — try relaxing your filters slightly.")
    else:
        st.warning("Please type something first.")

st.divider()

# ── AI AGENT ────────────────────────────────────────────
st.subheader("🧠 AI Agent — Full Recommendation")
st.caption("The agent searches, reads reviews, and reasons — not just filters")
st.info("⚡ The full AI Agent requires the local server. The search and filter features above work everywhere.")

st.caption("Built by Shivansh · Restaurant Intelligence Agent · Phase 6 of 6")