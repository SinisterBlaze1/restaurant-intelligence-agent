# Restaurant Intelligence Agent

## 🚀 Live Demo
[View the live dashboard →](https://restaurant-intelligence-agent-tvegy5snmgssdtrwbqrsll.streamlit.app/)

An end-to-end AI-powered restaurant discovery system built on real Zomato data.

## What it does
- Search 51,000+ Bangalore restaurants by cuisine, budget, area, and rating
- **Natural language search** — type what you want, AI extracts filters and queries 51,000+ restaurants
- **Analytics dashboard** — KPI cards, location benchmarking, cost vs rating visualisations
- **LangGraph agent** — searches restaurants, reads reviews, and produces a structured recommendation with reasoning
- **Automated pipeline** — n8n workflow that runs daily, fetches live stats, and emails a digest report

## Tech stack

| Layer | Technology |
|-------|-----------|
| Data | Zomato Bangalore dataset — 51,632 restaurants |
| ETL | Python, Pandas |
| Database | PostgreSQL (local) + Neon (cloud) |
| Backend | FastAPI (5 endpoints) |
| Frontend | Streamlit + Plotly |
| AI layer | Groq LLM — natural language to SQL |
| Agent | LangGraph multi-tool agent |
| Automation | n8n daily digest pipeline |

## Architecture
User query (plain English)
↓
Groq LLM — extracts filters
↓
PostgreSQL — runs SQL query
↓
LangGraph Agent
├── Tool 1: search_restaurants
├── Tool 2: get_reviews (RAG)
└── Tool 3: make_recommendation
↓
Structured recommendation with reasoning


## Project phases

- [x] Phase 1 — ETL pipeline + PostgreSQL + SQL analysis (8 analytical queries)
- [x] Phase 2 — FastAPI backend (5 REST endpoints)
- [x] Phase 3 — Streamlit analytics dashboard (KPI cards, charts, filters)
- [x] Phase 4 — LLM natural language search (Groq + structured outputs)
- [x] Phase 5 — LangGraph agentic system (3 tools, RAG over reviews)
- [x] Phase 6 — n8n automation pipeline + Streamlit Cloud deployment

## What I learned
- Real data is messy — the Zomato dataset had encoding issues, inconsistent cost formats, and duplicate listings requiring multi-step cleaning before any analysis was possible
- LLM structured outputs fail silently — building fallbacks at every parsing step is non-negotiable in production
- Small models hallucinate tool calls — switching from 8B to 70B model for the LangGraph agent was the difference between placeholder outputs and real recommendations
- Deployment separates frontend from heavy AI workloads — the dashboard and search run on Streamlit Cloud, the agentic layer runs on a dedicated local server

---

By- Shivansh Shekhar, DTU'27

## Setup
```bash
git clone https://github.com/YOUR-USERNAME/restaurant-intelligence-agent
cd restaurant-intelligence-agent
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```
