"""
FX Summary API - EUR to USD exchange rate analysis
Built for andiron-cursor skills test
"""

import json
import httpx
from pathlib import Path
from datetime import date
from typing import Literal
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI(
    title="FX Summary API",
    description="EUR to USD exchange rate summary with pattern analysis",
    version="1.0.0"
)

# Config
FRANKFURTER_BASE = "https://api.frankfurter.app"
FALLBACK_FILE = Path(__file__).parent / "data" / "sample_fx.json"
MAX_RETRIES = 3


# Pydantic models
class DayRate(BaseModel):
    date: str
    rate: float
    pct_change: float | None  # None for first day


class Totals(BaseModel):
    start_rate: float
    end_rate: float
    total_pct_change: float
    mean_rate: float


class SummaryResponse(BaseModel):
    breakdown: list[DayRate] | None  # None when breakdown='none'
    totals: Totals
    source: str  # 'api' or 'fallback'


class HealthResponse(BaseModel):
    status: str
    api_reachable: bool


# Shield of protection: retry with backoff
async def fetch_with_retry(client: httpx.AsyncClient, url: str) -> dict | None:
    """Fetch URL with retry logic. Returns None if all retries fail."""
    import asyncio

    for attempt in range(MAX_RETRIES):
        try:
            response = await client.get(url, timeout=10.0)
            response.raise_for_status()
            return response.json()
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            if attempt < MAX_RETRIES - 1:
                wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                await asyncio.sleep(wait_time)
            else:
                return None
    return None


def load_fallback() -> dict:
    """Load fallback data from local file."""
    with open(FALLBACK_FILE, "r") as f:
        return json.load(f)


def safe_pct_change(current: float, previous: float) -> float:
    """Calculate percentage change, guarding against division by zero."""
    if previous == 0:
        return 0.0  # Be kind when denominator is 0
    return round(((current - previous) / previous) * 100, 4)


def calculate_summary(rates_data: dict, breakdown_type: str) -> SummaryResponse:
    """Process rates data into summary response."""
    rates = rates_data.get("rates", {})

    if not rates:
        raise HTTPException(status_code=404, detail="No rate data available")

    # Sort by date
    sorted_dates = sorted(rates.keys())

    # Build day-by-day breakdown
    day_rates: list[DayRate] = []
    all_rates: list[float] = []
    previous_rate: float | None = None

    for d in sorted_dates:
        rate = rates[d].get("USD", 0.0)
        all_rates.append(rate)

        pct_change = None
        if previous_rate is not None:
            pct_change = safe_pct_change(rate, previous_rate)

        day_rates.append(DayRate(date=d, rate=rate, pct_change=pct_change))
        previous_rate = rate

    # Calculate totals
    start_rate = all_rates[0] if all_rates else 0.0
    end_rate = all_rates[-1] if all_rates else 0.0
    mean_rate = round(sum(all_rates) / len(all_rates), 4) if all_rates else 0.0
    total_pct_change = safe_pct_change(end_rate, start_rate)

    totals = Totals(
        start_rate=start_rate,
        end_rate=end_rate,
        total_pct_change=total_pct_change,
        mean_rate=mean_rate
    )

    return SummaryResponse(
        breakdown=day_rates if breakdown_type == "day" else None,
        totals=totals,
        source=rates_data.get("_source", "api")
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint - also tests API connectivity."""
    api_reachable = False

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{FRANKFURTER_BASE}/latest?from=EUR&to=USD", timeout=5.0)
            api_reachable = response.status_code == 200
        except httpx.RequestError:
            pass

    return HealthResponse(status="ok", api_reachable=api_reachable)


@app.get("/summary", response_model=SummaryResponse)
async def get_summary(
    start: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end: date = Query(..., description="End date (YYYY-MM-DD)"),
    breakdown: Literal["day", "none"] = Query("day", description="'day' for day-by-day, 'none' for totals only")
):
    """
    Get EUR to USD exchange rate summary for a date range.

    Returns daily rates with percentage changes and overall statistics.
    Falls back to local data if the Frankfurter API is unavailable.
    """
    if start > end:
        raise HTTPException(status_code=400, detail="Start date must be before end date")

    url = f"{FRANKFURTER_BASE}/{start}..{end}?from=EUR&to=USD"

    async with httpx.AsyncClient() as client:
        data = await fetch_with_retry(client, url)

    if data is None:
        # Fallback to local file
        data = load_fallback()
        data["_source"] = "fallback"
    else:
        data["_source"] = "api"

    return calculate_summary(data, breakdown)


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Simple visualization dashboard."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>FX Summary - EUR to USD</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                max-width: 900px;
                margin: 40px auto;
                padding: 20px;
                background: #f5f5f5;
            }
            h1 { color: #333; }
            .card {
                background: white;
                border-radius: 8px;
                padding: 20px;
                margin: 20px 0;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .form-row { margin: 10px 0; }
            label { display: inline-block; width: 100px; }
            input, select { padding: 8px; border: 1px solid #ddd; border-radius: 4px; }
            button {
                padding: 10px 20px;
                background: #007bff;
                color: white;
                border: none;
                border-radius: 4px;
                cursor: pointer;
            }
            button:hover { background: #0056b3; }
            table { width: 100%; border-collapse: collapse; margin: 20px 0; }
            th, td { padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }
            th { background: #f8f9fa; }
            .positive { color: #28a745; }
            .negative { color: #dc3545; }
            .totals { font-weight: bold; background: #e9ecef; }
            #chart-container { height: 300px; }
            .pineapple { font-size: 24px; }
        </style>
    </head>
    <body>
        <h1>FX Summary <span class="pineapple">🍍</span></h1>
        <p>EUR to USD exchange rate analysis</p>

        <div class="card">
            <h3>Query Parameters</h3>
            <div class="form-row">
                <label>Start Date:</label>
                <input type="date" id="start" value="2025-01-01">
            </div>
            <div class="form-row">
                <label>End Date:</label>
                <input type="date" id="end" value="2025-01-10">
            </div>
            <div class="form-row">
                <label>Breakdown:</label>
                <select id="breakdown">
                    <option value="day">Day by day</option>
                    <option value="none">Totals only</option>
                </select>
            </div>
            <div class="form-row">
                <button onclick="fetchData()">Fetch Rates</button>
            </div>
        </div>

        <div class="card" id="results" style="display:none;">
            <h3>Results <span id="source-badge"></span></h3>
            <div id="chart-container">
                <canvas id="chart"></canvas>
            </div>
            <table id="data-table"></table>
        </div>

        <script>
            let chart = null;

            async function fetchData() {
                const start = document.getElementById('start').value;
                const end = document.getElementById('end').value;
                const breakdown = document.getElementById('breakdown').value;

                try {
                    const response = await fetch(`/summary?start=${start}&end=${end}&breakdown=${breakdown}`);
                    const data = await response.json();

                    if (!response.ok) {
                        alert(data.detail || 'Error fetching data');
                        return;
                    }

                    displayResults(data);
                } catch (err) {
                    alert('Network error: ' + err.message);
                }
            }

            function displayResults(data) {
                document.getElementById('results').style.display = 'block';
                document.getElementById('source-badge').textContent =
                    data.source === 'fallback' ? '(using fallback data)' : '(live data)';

                // Build table
                let tableHtml = '<tr><th>Date</th><th>Rate (EUR→USD)</th><th>Change</th></tr>';

                if (data.breakdown) {
                    data.breakdown.forEach(day => {
                        const changeClass = day.pct_change > 0 ? 'positive' : (day.pct_change < 0 ? 'negative' : '');
                        const changeStr = day.pct_change !== null ? `${day.pct_change > 0 ? '+' : ''}${day.pct_change}%` : '-';
                        tableHtml += `<tr><td>${day.date}</td><td>${day.rate.toFixed(4)}</td><td class="${changeClass}">${changeStr}</td></tr>`;
                    });
                }

                // Totals row
                const t = data.totals;
                const totalClass = t.total_pct_change > 0 ? 'positive' : (t.total_pct_change < 0 ? 'negative' : '');
                tableHtml += `<tr class="totals"><td>Total</td><td>Mean: ${t.mean_rate.toFixed(4)}</td><td class="${totalClass}">${t.total_pct_change > 0 ? '+' : ''}${t.total_pct_change}%</td></tr>`;

                document.getElementById('data-table').innerHTML = tableHtml;

                // Chart
                if (data.breakdown && data.breakdown.length > 0) {
                    const ctx = document.getElementById('chart').getContext('2d');

                    if (chart) chart.destroy();

                    chart = new Chart(ctx, {
                        type: 'line',
                        data: {
                            labels: data.breakdown.map(d => d.date),
                            datasets: [{
                                label: 'EUR to USD',
                                data: data.breakdown.map(d => d.rate),
                                borderColor: '#007bff',
                                backgroundColor: 'rgba(0,123,255,0.1)',
                                fill: true,
                                tension: 0.1
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: { display: false }
                            },
                            scales: {
                                y: {
                                    beginAtZero: false,
                                    title: { display: true, text: 'Rate' }
                                }
                            }
                        }
                    });
                }
            }
        </script>
    </body>
    </html>
    """
    return html


# 🍍 Pineapple by the door
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
