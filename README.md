# 🚚 Supply Chain AI Agent
### Autonomous Risk & Decision System for Indian Logistics

> A production-quality, multi-agent FastAPI backend with a self-contained HTML dashboard. Built for the India logistics context — real supplier names, INR pricing, named national highways, and live weather corridor data.

---

## 📊 Hackathon Audit Score — 20/25

| Criterion | Score |
|---|---|
| Domain Expertise Depth | 4 / 5 |
| Compliance & Guardrail Enforcement | 4 / 5 |
| Edge-Case Handling | 3 / 5 |
| Full Task Completion | 5 / 5 |
| Auditability of Every Decision | 4 / 5 |

> *"Strong production-quality prototype. Architecture is clean and end-to-end."*

---

## 🏗️ Architecture

```
POST /analyze
      │
      ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  DataAgent  │───▶│  RiskAgent  │───▶│ RouteAgent  │
│             │    │             │    │             │
│ Weather API │    │ weather 55% │    │ Risk 50%    │
│ Supplier DB │    │ supplier 45%│    │ Time  30%   │
│ Route DB    │    │ + distance  │    │ Cost  20%   │
└─────────────┘    └─────────────┘    └──────┬──────┘
                                             │
      ┌──────────────────────────────────────┘
      ▼
┌──────────────┐   ┌──────────────────┐   ┌────────────┐
│ DecisionAgent│──▶│ ComplianceAgent  │──▶│  LLMAgent  │
│              │   │                  │   │            │
│ risk ≤ 60 →  │   │ SLA / deadline   │   │ Gemini 2.5 │
│   PROCEED    │   │ cost threshold   │   │ Flash +    │
│ risk > 60 →  │   │ CRITICAL flag    │   │ template   │
│   REROUTE    │   │ high-value alert │   │ fallback   │
└──────────────┘   └──────────────────┘   └─────┬──────┘
                                                 │
                                          ┌──────▼──────┐
                                          │  AuditAgent │
                                          │             │
                                          │ trace_id    │
                                          │ flat record │
                                          │ → JSON log  │
                                          └─────────────┘
```

**7-agent sequential pipeline.** Each agent appends a structured step to the audit trail — agent name, action label, status (`SUCCESS` / `WARNING` / `ERROR`), details, and UTC ISO-8601 timestamp.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | FastAPI + Uvicorn (Python 3.12) |
| **Frontend** | Single-file HTML dashboard (no Streamlit) |
| **LLM** | Google Gemini 2.5 Flash via `google-genai` |
| **Weather** | WeatherAPI.com — live corridor severity |
| **Data** | CSV-backed supplier & route databases |
| **Validation** | Pydantic v2 models |
| **Context** | India logistics — INR pricing, national highways |

---

## ⚡ Quick Start

### 1. Clone & create environment

```bash
git clone <your-repo-url>
cd supply-chain-ai-agent

conda create -n supply-chain python=3.12 -y
conda activate supply-chain
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure API keys

Create a `.env` file in the project root:

```env
WEATHER_API_KEY=your_weatherapi_com_key
LLM_API_KEY=your_google_ai_studio_key

# Optional overrides (defaults shown)
RISK_THRESHOLD=60
MAX_COST_THRESHOLD=150000
SLA_MAX_DELAY_DAYS=7
```

### 4. Run the server

```bash
python -m app.main
```

### 5. Open in browser

| Interface | URL |
|---|---|
| 📊 Dashboard | http://localhost:8000/ |
| 📖 Swagger UI | http://localhost:8000/docs |

---

## 📁 Project Structure

```
supply-chain-ai-agent/
│
├── app/
│   ├── agents/
│   │   ├── data_agent/          # Fetches weather, supplier profile, routes
│   │   ├── risk_agent/          # Composite risk scoring (weather + supplier + distance)
│   │   ├── route_agent/         # Route optimisation — ranks all routes by composite score
│   │   ├── decision_agent/      # PROCEED / REROUTE at risk threshold 60
│   │   ├── compliance_agent/    # SLA, deadline, cost threshold, CRITICAL guardrails
│   │   ├── llm_agent/           # Gemini 2.5 Flash — template fallback on API failure
│   │   └── audit_agent/         # Persists full pipeline trace → logs/audit_logs.json
│   │
│   ├── config/
│   │   └── settings.py          # Pydantic settings loaded from .env
│   │
│   ├── models/                  # Pydantic I/O models
│   │
│   ├── routes/
│   │   ├── api_routes.py        # POST /analyze, POST /analyze/csv, GET /audit/logs
│   │   ├── analytics_routes.py  # GET /analytics/overview, risk, supplier, route perf
│   │   ├── fleet_routes.py      # Live fleet monitor (status derived from audit index)
│   │   └── export_routes.py     # CSV / JSON audit export
│   │
│   ├── services/
│   │   ├── llm_service/         # Gemini API connector
│   │   ├── weather_service/     # WeatherAPI.com connector
│   │   ├── route_service/       # CSV route loader
│   │   ├── supplier_service/    # CSV supplier loader
│   │   └── file_service/        # Bulk CSV upload parser
│   │
│   ├── utils/                   # Helpers, logger, validators
│   └── main.py                  # FastAPI app + static file serving
│
├── frontend/
│   └── static/
│       └── index.html           # Self-contained dashboard (no Streamlit)
│
├── data/
│   ├── suppliers.csv            # 15 Indian suppliers (Blue Dart, GATI, Safexpress, VRL …)
│   ├── routes.csv               # 15 named-highway routes (NH-48, NH-44, NH-65, RAIL …)
│   └── shipments.csv            # 10 sample shipments for bulk demo
│
├── logs/
│   ├── audit_logs.json          # Structured decision audit (FIFO, max 500 records)
│   └── system_logs.log          # Operational logs (separate from audit trail)
│
├── seed_chart_data.py           # Utility to pre-populate analytics charts
├── requirements.txt
└── .env
```

---

## 🌐 API Reference

### Core Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | HTML dashboard |
| `GET` | `/api/v1/health` | Health check |
| `POST` | `/api/v1/analyze` | Run 7-agent pipeline for a single shipment |
| `POST` | `/api/v1/analyze/csv` | Bulk CSV analysis (all 10 sample shipments) |
| `GET` | `/api/v1/audit/logs` | Recent audit log entries |
| `GET` | `/docs` | Swagger UI — full interactive spec |

### Analytics Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/analytics/overview` | Summary stats |
| `GET` | `/api/v1/analytics/risk-distribution` | Risk score breakdown |
| `GET` | `/api/v1/analytics/supplier-performance` | Per-supplier metrics |
| `GET` | `/api/v1/analytics/route-performance` | Per-route metrics |

### Export Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/export/audit-logs/json` | Download full audit log as JSON |
| `GET` | `/api/v1/export/audit-logs/csv` | Download audit log as CSV |

### Fleet Monitor

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/fleet/monitor` | Live AT_RISK / ON_SCHEDULE / DELAYED status derived from audit index |

---

## 🤖 Agent Pipeline — Details

### 1 · DataAgent
Fetches live weather via WeatherAPI.com for origin and destination cities. Loads supplier profile from `suppliers.csv` and all candidate routes from `routes.csv`. Weather severity is a weighted corridor score: origin (60%) + destination (40%), incorporating wind speed, precipitation, and visibility penalties.

### 2 · RiskAgent
Computes a composite risk score `[0–100]`:
```
risk = (weather_severity × 0.55) + (supplier_risk × 0.45) + distance_penalty
```
`CRITICAL` priority shipments incur an additional 10% penalty and a mandatory human-review flag. All values are clamped — confidence `[0.75, 0.99]`, delay probability `[0.05, 0.95]`.

### 3 · RouteAgent
Ranks all routes by a composite optimisation score:
```
score = (risk × 0.50) + (time × 0.30) + (cost × 0.20)
```
Selects the highest-risk route as `current` and the best non-current route as `alternate`. Each alternate is annotated with a score-delta reason string.

### 4 · DecisionAgent
Emits `PROCEED` if `risk_score ≤ 60`, otherwise `REROUTE`. Writes a human-readable `decision_reason` string (threshold comparison) to the pipeline context.

### 5 · ComplianceAgent
Validates five rules in sequence:

| Rule | Logic |
|---|---|
| SLA delay check | `estimated_delay_days ≤ sla_max_delay_days` (default 7 days) |
| Deadline reachability | `days_remaining` vs estimated delay |
| Freight cost threshold | `route_cost ≤ Rs. 1,50,000` (configurable) |
| CRITICAL hard guardrail | Always triggers mandatory human-review violation |
| High-value advisory | Shipments > Rs. 1 crore → insurance verification note (soft) |

### 6 · LLMAgent
Calls Gemini 2.5 Flash to generate a natural-language explanation referencing exact numbers (risk score, delay probability, rerouting highway). Falls back to a deterministic template on `400 / 429 / timeout` — the system never returns a blank explanation.

### 7 · AuditAgent
Serialises a flat record to `logs/audit_logs.json` with: `trace_id` (SC-XXXXXXXXXXXX hex), timestamps, all shipment/risk/decision/compliance fields, violations list, and full `pipeline_steps` array. Bounded to 500 entries with FIFO eviction. A separate `system_logs.log` keeps operational logs isolated from the decision audit trail.

---

## 🛡️ Compliance & Guardrails

| Scenario | Behaviour |
|---|---|
| Weather API failure | Falls back to `severity=0.30`, pipeline continues, `WARNING` in audit |
| Supplier not in CSV | Uses `reliability=0.50` default (`MEDIUM` tier), logged as `WARNING` |
| No routes in database | `RouteAgent` skips optimisation, pipeline continues with empty route context |
| Gemini API failure | Template fallback, `audit step status = WARNING` |
| Corrupt audit log | `_load_existing_logs()` catches `OSError / JSONDecodeError`, re-writes cleanly |
| Unknown numeric values | All scores clamped to valid ranges — no impossible values propagate |

---

## 🗄️ Data

**Suppliers (`data/suppliers.csv`)** — 15 Indian logistics providers including Blue Dart, GATI, Safexpress, VRL Logistics, and Patel Roadways. Each has a reliability score, average delay days, on-time rate, risk tier (`LOW / MEDIUM / HIGH / CRITICAL`), and incident count.

**Routes (`data/routes.csv`)** — 15 named-highway routes across major Indian corridors (NH-48, NH-44, NH-65, RAIL). Fields include distance (km), estimated time (hours), freight cost (INR), toll gates, and base risk score.

**Sample shipments (`data/shipments.csv`)** — 10 pre-configured shipments covering varied origins, priorities, and deadlines for bulk demo via `POST /analyze/csv`.

---

## 🔧 Configuration Reference

All settings are loaded from `.env` via Pydantic's `BaseSettings`. No hardcoded values in application code.

| Variable | Default | Description |
|---|---|---|
| `WEATHER_API_KEY` | — | WeatherAPI.com key (required) |
| `LLM_API_KEY` | — | Google AI Studio key (required) |
| `RISK_THRESHOLD` | `60` | Score above which REROUTE is triggered |
| `MAX_COST_THRESHOLD` | `150000` | Freight cost ceiling in INR |
| `SLA_MAX_DELAY_DAYS` | `7` | Maximum tolerable delay in days |
| `APP_HOST` | `0.0.0.0` | Server bind address |
| `APP_PORT` | `8000` | Server port |

---

## 🤝 Collaboration — Git Workflow

```bash
# First push (set upstream)
git add .
git commit -m "feat: your change description"
git push --set-upstream origin main

# Subsequent pushes
git add .
git commit -m "fix: your fix description"
git push origin main

# Quick push (any change)
git add .
git commit -m "update"
git push




```

---

## 📋 Requirements

See [`requirements.txt`](requirements.txt) for the full list. Key dependencies:

```
fastapi==0.111.0
uvicorn[standard]==0.29.0
pydantic==2.7.1
pydantic-settings==2.3.0
google-genai>=1.0.0
httpx==0.27.0
pandas==2.2.2
python-dotenv==1.0.1
```

---

*Supply Chain AI Agent · Hackathon Build Sprint · March 2026*
