# FX Summary API

andiron-cursor ✅

EUR to USD exchange rate summary with pattern analysis. Built with FastAPI.

🍍

## Quick Start

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the server
python main.py
# or
uvicorn main:app --reload --port 8000
```

Server runs on http://localhost:8000

## Endpoints

### `GET /health`

Health check. Also tests Frankfurter API connectivity.

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "ok",
  "api_reachable": true
}
```

### `GET /summary`

Get EUR to USD exchange rate summary for a date range.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `start` | date | Yes | Start date (YYYY-MM-DD) |
| `end` | date | Yes | End date (YYYY-MM-DD) |
| `breakdown` | string | No | `day` (default) or `none` |

**Example - Day by day:**
```bash
curl "http://localhost:8000/summary?start=2025-01-01&end=2025-01-07&breakdown=day"
```

Response:
```json
{
  "breakdown": [
    { "date": "2025-01-01", "rate": 1.0352, "pct_change": null },
    { "date": "2025-01-02", "rate": 1.0311, "pct_change": -0.3961 },
    { "date": "2025-01-03", "rate": 1.0295, "pct_change": -0.1552 },
    { "date": "2025-01-06", "rate": 1.0384, "pct_change": 0.8645 },
    { "date": "2025-01-07", "rate": 1.0342, "pct_change": -0.4045 }
  ],
  "totals": {
    "start_rate": 1.0352,
    "end_rate": 1.0342,
    "total_pct_change": -0.0966,
    "mean_rate": 1.0337
  },
  "source": "api"
}
```

**Example - Totals only:**
```bash
curl "http://localhost:8000/summary?start=2025-01-01&end=2025-01-07&breakdown=none"
```

Response:
```json
{
  "breakdown": null,
  "totals": {
    "start_rate": 1.0352,
    "end_rate": 1.0342,
    "total_pct_change": -0.0966,
    "mean_rate": 1.0337
  },
  "source": "api"
}
```

### `GET /`

Interactive dashboard with chart visualization.

Open http://localhost:8000 in your browser.

## Features

- **Day-by-day breakdown** with percentage change from prior day
- **Totals** including start rate, end rate, total change, and mean rate
- **Fallback to local data** when Frankfurter API is unavailable
- **Retry with exponential backoff** (3 attempts: 1s, 2s, 4s delays)
- **Division by zero protection** - returns 0 when denominator is 0
- **Interactive dashboard** with Chart.js visualization

## Data Source

Primary: [Frankfurter API](https://api.frankfurter.dev) (no API key required)

Fallback: `data/sample_fx.json` when network fails

## Tech Stack

- FastAPI
- Pydantic
- httpx (async HTTP client)
- Chart.js (frontend visualization)

## API Docs

FastAPI auto-generates documentation:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
