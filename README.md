# Restaurant Intelligence Agent

## 🚀 Live Demo
[View the live dashboard →](https://restaurant-intelligence-agent-tvegy5snmgssdtrwbqrsll.streamlit.app/)

An end-to-end AI-powered restaurant discovery system built on real Zomato data.

## What it does
- Search 51,000+ Bangalore restaurants by cuisine, budget, area, and rating
- Natural language search — type what you want, AI extracts the filters
- Analytics dashboard with insights on ratings, costs, and location trends

## Tech stack
- **Data**: Zomato Bangalore dataset (51,632 restaurants)
- **Database**: PostgreSQL
- **Backend**: FastAPI
- **Frontend**: Streamlit + Plotly
- **AI Layer**: LLM-powered natural language to SQL
- **Automation**: n8n pipeline (Phase 5)

## Phases
- [x] Phase 1 — Data layer (ETL, PostgreSQL, SQL queries)
- [x] Phase 2 — Search API (FastAPI endpoints)
- [x] Phase 3 — Analytics dashboard (Streamlit, Plotly charts)
- [ ] Phase 4 — LLM layer (natural language search)
- [ ] Phase 5 — Agentic system (LangGraph, multi-tool agent)
- [ ] Phase 6 — n8n automation + deployment

## Setup
```bash
git clone https://github.com/YOUR-USERNAME/restaurant-intelligence-agent
cd restaurant-intelligence-agent
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```
