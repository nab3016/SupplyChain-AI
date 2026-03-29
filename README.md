# Supply Chain AI — Autonomous Risk & Decision System

Multi-agent FastAPI backend with a self-contained HTML frontend.

## Stack
- **Backend**: FastAPI + Uvicorn (Python 3.12)
- **Frontend**: Single HTML file (`frontend/static/index.html`) — no Streamlit
- **LLM**: Google Gemini 2.5 Flash via `google-genai`
- **Weather**: WeatherAPI.com live corridor data
- **Data**: CSV-backed supplier & route databases

## Quick Start

```bash
# 1. Create conda environment
conda create -n supply-chain python=3.12 -y
conda activate supply-chain

# 2. Install dependencies
pip install -r requirements.txt

# 3. Add your API keys to .env
#    WEATHER_API_KEY = your WeatherAPI.com key
#    LLM_API_KEY     = your Google AI Studio key

# 4. Run
python -m app.main

# 5. Open browser
#    UI  →  http://localhost:8000/
#    API →  http://localhost:8000/docs
```

## Project Structure

```
supply-chain-ai-agent/
├── app/
│   ├── agents/
│   │   ├── audit_agent/        # Persists pipeline trace to JSON
│   │   ├── compliance_agent/   # SLA + cost validation
│   │   ├── data_agent/         # Fetches weather, supplier, routes
│   │   ├── decision_agent/     # PROCEED / REROUTE decision
│   │   ├── llm_agent/          # Gemini explanation generator
│   │   ├── risk_agent/         # Composite risk scoring
│   │   └── route_agent/        # Route optimisation
│   ├── config/
│   │   └── settings.py         # Pydantic settings from .env
│   ├── models/                 # Pydantic I/O models
│   ├── routes/
│   │   └── api_routes.py       # POST /analyze, GET /health
│   ├── services/
│   │   ├── llm_service/        # Gemini API connector
│   │   ├── weather_service/    # WeatherAPI.com connector
│   │   ├── route_service/      # CSV route loader
│   │   ├── supplier_service/   # CSV supplier loader
│   │   └── file_service/       # CSV upload parser
│   ├── utils/                  # Helpers, logger, validators
│   └── main.py                 # FastAPI app + static file serving
├── frontend/
│   └── static/
│       └── index.html          # Self-contained UI (no Streamlit)
├── data/
│   ├── routes.csv
│   ├── shipments.csv
│   └── suppliers.csv
├── logs/
│   ├── audit_logs.json
│   └── system_logs.log
├── .env
└── requirements.txt
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | HTML dashboard |
| GET | `/api/v1/health` | Health check |
| POST | `/api/v1/analyze` | Run 7-agent pipeline |
| POST | `/api/v1/analyze/csv` | Bulk CSV analysis |
| GET | `/api/v1/audit/logs` | Recent audit log entries |
| GET | `/docs` | Swagger UI |
