import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

BASE_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="Restaurant Intelligence",
    page_icon="🍽️",
    layout="wide"
)

st.title("🍽️ Restaurant Intelligence Dashboard")
st.caption("Bangalore restaurant data · 51,632 restaurants · Powered by Zomato dataset")

# ── KPI CARDS ──────────────────────────────────────────
st.subheader("Overview")

insights = requests.get(f"{BASE_URL}/insights").json()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Restaurants", f"{insights['total_restaurants']:,}")
col2.metric("Average Rating", f"{insights['avg_rating']} / 5")
col3.metric("Average Cost for Two", f"₹{int(insights['avg_cost'])}")
col4.metric("Offer Online Order", f"{insights['online_order_count']:,}")

st.divider()

# ── INSIGHT CARDS ──────────────────────────────────────
st.subheader("Key Findings")

i1, i2, i3, i4 = st.columns(4)
i1.info("📍 **Lavelle Road** has the highest average rating among all Bangalore areas")
i2.info("📱 Restaurants with **online ordering** rate higher on average (3.72 vs 3.66)")
i3.info("💎 **Premium restaurants** (₹1000+) have the highest average ratings")
i4.info("📅 Restaurants with **table booking** get 5.7x more votes on average")

st.divider()

# ── TOP LOCATIONS CHART ─────────────────────────────────
st.subheader("Top 10 Areas by Average Rating")

locations = requests.get(f"{BASE_URL}/top-locations").json()
loc_df = pd.DataFrame(locations)

fig1 = px.bar(
    loc_df,
    x="avg_rating",
    y="location",
    orientation="h",
    color="avg_rating",
    color_continuous_scale="Teal",
    text="avg_rating",
    labels={"avg_rating": "Avg Rating", "location": "Area"},
)
fig1.update_traces(textposition="outside")
fig1.update_layout(
    height=400,
    coloraxis_showscale=False,
    yaxis=dict(categoryorder="total ascending")
)
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
    params = {
        "min_rating": min_rating,
        "max_cost": max_cost,
        "limit": 50
    }
    if cuisine_input:
        params["cuisine"] = cuisine_input
    if location_input:
        params["location"] = location_input
    if online_only:
        params["online_order"] = True

    response = requests.get(f"{BASE_URL}/search", params=params).json()

    if response:
        results_df = pd.DataFrame(response)
        st.success(f"Found {len(results_df)} restaurants")

        # Results table
        st.dataframe(
            results_df[["name", "location", "cuisines", "rate", "approx_cost", "votes"]],
            column_config={
                "rate": st.column_config.ProgressColumn(
                    "Rating", min_value=0, max_value=5, format="%.1f"
                ),
                "approx_cost": st.column_config.NumberColumn(
                    "Cost for Two", format="₹%d"
                ),
            },
            use_container_width=True,
            hide_index=True
        )

        # Mini chart for search results
        if len(results_df) > 3:
            st.subheader("Rating distribution in results")
            fig2 = px.histogram(
                results_df,
                x="rate",
                nbins=10,
                color_discrete_sequence=["#0ea5e9"]
            )
            fig2.update_layout(height=300)
            st.plotly_chart(fig2, use_container_width=True)
    else:
        st.warning("No restaurants found. Try relaxing your filters.")

st.divider()

# ── COST vs RATING SCATTER ──────────────────────────────
st.subheader("Cost vs Rating — Top 300 restaurants by votes")

top_df = pd.DataFrame(
    requests.get(f"{BASE_URL}/restaurants", params={"limit": 300}).json()
)

if not top_df.empty and "rate" in top_df.columns:
    fig3 = px.scatter(
        top_df,
        x="approx_cost",
        y="rate",
        hover_name="name",
        hover_data=["location", "votes"],
        color="rate",
        color_continuous_scale="RdYlGn",
        labels={"approx_cost": "Cost for Two (₹)", "rate": "Rating"},
        size="votes",
        size_max=25
    )
    fig3.update_layout(height=450, coloraxis_showscale=False)
    st.plotly_chart(fig3, use_container_width=True)

st.divider()
st.subheader("🤖 Ask in Plain English")
st.caption("Describe what you want — AI figures out the filters")

nl_query = st.text_input(
    "What are you looking for?",
    placeholder="e.g. Best biryani under ₹600 near Indiranagar with online ordering"
)

if st.button("Ask AI", type="primary"):
    if nl_query.strip():
        with st.spinner("Thinking..."):
            response = requests.post(
                f"{BASE_URL}/ai-search",
                json={"query": nl_query}
            ).json()

        filters = response.get("filters_extracted", {})
        st.markdown("**Filters extracted by AI:**")
        fcol1, fcol2, fcol3, fcol4 = st.columns(4)
        fcol1.metric("Cuisine", filters.get("cuisine") or "Any")
        fcol2.metric("Area", filters.get("location") or "Any")
        fcol3.metric("Max Cost", f"₹{filters.get('max_cost') or 2000}")
        fcol4.metric("Min Rating", filters.get("min_rating") or 3.5)

        results = response.get("results", [])
        if results:
            st.success(f"Found {len(results)} restaurants")
            ai_df = pd.DataFrame(results)
            st.dataframe(
                ai_df[["name", "location", "cuisines",
                        "rate", "approx_cost", "votes"]],
                column_config={
                    "rate": st.column_config.ProgressColumn(
                        "Rating", min_value=0, max_value=5, format="%.1f"
                    ),
                    "approx_cost": st.column_config.NumberColumn(
                        "Cost for Two", format="₹%d"
                    ),
                },
                use_container_width=True,
                hide_index=True
            )
        else:
            st.warning("No results found — try relaxing your filters slightly.")
    else:
        st.warning("Please type something first.")

st.divider()
st.subheader("🧠 AI Agent — Full Recommendation")
st.caption("The agent searches, reads reviews, and reasons — not just filters")

agent_query = st.text_input(
    "Ask the agent anything",
    placeholder="e.g. Best place for a date night under ₹2000 in Indiranagar",
    key="agent_input"
)

if st.button("Ask Agent", type="primary", key="agent_btn"):
    if agent_query.strip():
        with st.spinner("Agent is thinking — searching, reading reviews, reasoning..."):
            try:
                response = requests.post(
                    f"{BASE_URL}/agent",
                    json={"query": agent_query},
                    timeout=120
                ).json()

                if "error" in response:
                    error_msg = response["error"]
                    if "rate_limit" in error_msg or "429" in error_msg:
                        st.warning("⏳ Groq rate limit reached. Wait 10 minutes and try again — you've used today's free token quota.")
                    else:
                        st.error(f"Agent error: {error_msg[:200]}")
                else:
                    recommendation = response.get("recommendation", "")
                    if recommendation and len(recommendation) > 20:
                        st.markdown("### 🍽️ Agent's Recommendation")
                        lines = [
                            l.strip() for l in recommendation.strip().split('\n')
                            if l.strip() and not set(l.strip()).issubset({'─', '-', ' '})
                        ]
                        for line in lines:
                            if "RECOMMENDATION:" in line:
                                name = line.replace("🍽️ RECOMMENDATION:", "").replace("RECOMMENDATION:", "").strip()
                                st.markdown(f"## {name}")
                            else:
                                st.markdown(line)
                    else:
                        st.warning("Agent returned an empty response. Try again.")
            except requests.exceptions.Timeout:
                st.warning("⏳ Agent timed out. The model is slow on free tier — try again.")
            except Exception as e:
                st.error(f"Connection error: {str(e)}")
    else:
        st.warning("Please type something first.")

st.caption("Built by Shivansh · Restaurant Intelligence Agent · Phase 3 of 5")