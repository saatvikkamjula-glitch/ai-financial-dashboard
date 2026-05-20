# AI Financial Dashboard

An AI-powered financial dashboard built with Python. It tracks a stock portfolio, watchlist stocks, recent stock news, alerts, charts, and AI-generated portfolio summaries using local AI through Ollama/Llama 3.2.

This project is designed as a beginner-friendly finance and AI automation project.

---

## Features

- Tracks a personal stock portfolio
- Tracks a separate stock watchlist
- Pulls stock data using `yfinance`
- Creates interactive charts using Plotly
- Generates an AI portfolio summary using Ollama/Llama 3.2
- Shows recent stock news for portfolio and watchlist stocks
- Displays a moving stock ticker
- Shows portfolio gain/loss and allocation
- Shows watchlist movers and research signals
- Checks automatic alerts for both portfolio and watchlist stocks
- Opens the dashboard automatically as an HTML report
- Supports manual running anytime
- Supports scheduled daily running on Mac

---

## Main Dashboard Sections

The dashboard includes:

- Total portfolio value
- Daily gain/loss
- Total gain/loss compared to average cost
- Best and worst owned stock
- Largest portfolio position
- Watchlist movers
- Portfolio alerts
- Watchlist alerts
- AI summary
- Portfolio metrics table
- Watchlist metrics table
- Portfolio news
- Watchlist news
- Portfolio allocation chart
- Gain/loss charts
- Moving average charts
- Volatility chart

---

## Tech Stack

- Python
- pandas
- yfinance
- Plotly
- Ollama
- Llama 3.2
- HTML/CSS
- macOS LaunchAgent scheduler
- Git/GitHub

---

## Project Structure

```text
finance-dashboard/
├── main.py
├── alert_checker.py
├── portfolio.csv
├── watchlist.csv
├── README.md
├── requirements.txt
├── run_dashboard.command
├── run_dashboard_scheduled.command
├── com.finance.dashboard.plist
├── .gitignore
├── reports/
└── venv/