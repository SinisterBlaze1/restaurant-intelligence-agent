import os
import json
from typing import TypedDict, Annotated
from dotenv import load_dotenv
from pathlib import Path

import sys
import uuid
sys.modules['uuid_utils'] = uuid
sys.modules['uuid_utils.compat'] = uuid

# Your existing imports below...
from langchain_groq import ChatGroq

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from sqlalchemy import text
from app.database import engine

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

# ── LLM ────────────────────────────────────────────────
llm = ChatGroq(
    api_key=os.getenv("GROQ_API_KEY"),
    model="llama-3.3-70b-versatile",
    temperature=0
)

# ── TOOL 1: Search restaurants ──────────────────────────
@tool
def search_restaurants(
    cuisine: str = None,
    location: str = None,
    max_cost: int = 2000,
    min_rating: float = 3.5,
    limit: int = 5
) -> str:
    """Search restaurants by cuisine, location, budget and rating.
    Use this first to find matching restaurants."""

    conditions = [
        "rate IS NOT NULL",
        "approx_cost IS NOT NULL",
        "rate >= :min_rating",
        "approx_cost <= :max_cost"
    ]
    params = {
        "min_rating": min_rating,
        "max_cost": max_cost,
        "limit": limit
    }

    if cuisine:
        conditions.append("cuisines ILIKE :cuisine")
        params["cuisine"] = f"%{cuisine}%"
    if location:
        conditions.append("location ILIKE :location")
        params["location"] = f"%{location}%"

    where_clause = " AND ".join(conditions)

    query = text(f"""
        SELECT name, location, cuisines, rate, approx_cost, votes
        FROM (
            SELECT DISTINCT ON (name)
                name, location, cuisines, rate, approx_cost, votes
            FROM restaurants
            WHERE {where_clause}
            ORDER BY name, rate DESC
        ) deduped
        ORDER BY rate DESC, votes DESC
        LIMIT :limit
    """)

    with engine.connect() as conn:
        result = conn.execute(query, params)
        rows = [dict(r) for r in result.mappings().all()]

    if not rows:
        return "No restaurants found matching those criteria."

    output = f"Found {len(rows)} restaurants:\n"
    for i, r in enumerate(rows, 1):
        output += f"{i}. {r['name']} ({r['location']}) — {r['cuisines']} — Rating: {r['rate']} — Cost for two: Rs {r['approx_cost']} — Votes: {r['votes']}\n"
    return output


# ── TOOL 2: Get reviews ─────────────────────────────────
@tool
def get_reviews(restaurant_name: str) -> str:
    """Get customer reviews for a specific restaurant.
    Use this after finding restaurants to understand what customers say."""

    query = text("""
        SELECT review_text, rating
        FROM reviews
        WHERE restaurant_name ILIKE :name
        LIMIT 5
    """)

    with engine.connect() as conn:
        result = conn.execute(query, {"name": f"%{restaurant_name}%"})
        rows = [dict(r) for r in result.mappings().all()]

    if not rows:
        return f"No reviews found for {restaurant_name}."

    output = f"Reviews for {restaurant_name}:\n"
    for r in rows:
        output += f"- {r['review_text']}\n"
    return output


# ── TOOL 3: Recommend ───────────────────────────────────
@tool
def make_recommendation(
    restaurant_name: str,
    rating: float,
    cost: int,
    votes: int,
    review_summary: str,
    user_budget: int = None
) -> str:
    """Make a final recommendation for a restaurant with full reasoning.
    Use this last after you have search results and reviews."""

    budget_fit = ""
    if user_budget:
        if cost <= user_budget:
            budget_fit = f"✓ Within budget (Rs {cost} vs your Rs {user_budget} budget)"
        else:
            budget_fit = f"⚠ Slightly over budget (Rs {cost} vs your Rs {user_budget} budget)"

    popularity = "very popular" if votes > 1000 else "moderately popular" if votes > 200 else "lesser known"

    recommendation = f"""
🍽️ RECOMMENDATION: {restaurant_name}
{'─' * 40}
⭐ Rating: {rating}/5
💰 Cost for two: Rs {cost} {f'({budget_fit})' if budget_fit else ''}
👥 Popularity: {popularity} ({votes} votes)
📝 What customers say: {review_summary}
✅ Verdict: {'Highly recommended' if rating >= 4.3 else 'Good choice' if rating >= 4.0 else 'Decent option'}
"""
    return recommendation


# ── AGENT STATE ─────────────────────────────────────────
class AgentState(TypedDict):
    messages: Annotated[list, lambda x, y: x + y]


# ── BUILD THE GRAPH ─────────────────────────────────────
tools = [search_restaurants, get_reviews, make_recommendation]
llm_with_tools = llm.bind_tools(tools)
tool_node = ToolNode(tools)

SYSTEM_PROMPT = """You are a restaurant recommendation agent for Bangalore.

You have 3 tools:
1. search_restaurants — find restaurants by cuisine, location, budget, rating
2. get_reviews — get customer reviews for a specific restaurant  
3. make_recommendation — produce a final recommendation with reasoning

Always follow this sequence:
Step 1: Call search_restaurants with the user's criteria
Step 2: Call get_reviews for the TOP result from step 1
Step 3: Call make_recommendation with all the information you have gathered

Never skip steps. Always complete all 3 tool calls before giving your final answer."""


def agent_node(state: AgentState):
    messages = state["messages"]
    if not any(isinstance(m, SystemMessage) for m in messages):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}


def should_continue(state: AgentState):
    last = state["messages"][-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"
    return END


# ── COMPILE GRAPH ───────────────────────────────────────
graph = StateGraph(AgentState)
graph.add_node("agent", agent_node)
graph.add_node("tools", tool_node)
graph.set_entry_point("agent")
graph.add_conditional_edges("agent", should_continue, {
    "tools": "tools",
    END: END
})
graph.add_edge("tools", "agent")

agent = graph.compile()


# ── PUBLIC FUNCTION ─────────────────────────────────────
def run_agent(user_query: str) -> str:
    result = agent.invoke({
        "messages": [HumanMessage(content=user_query)]
    })
    # Get the last text message
    for msg in reversed(result["messages"]):
        if hasattr(msg, "content") and msg.content and not hasattr(msg, "tool_calls"):
            return msg.content
    return "Could not generate recommendation."