# AI Financial Dashboard

An AI-powered financial dashboard built with Python. It tracks a stock portfolio, watchlist stocks, recent stock news, alerts, benchmark performance, sector allocation, dividends, earnings dates, and AI-generated summaries using local AI through Ollama/Llama 3.2.

This project is designed as a beginner-friendly finance and AI automation project. It combines finance, data analysis, AI summaries, automated reporting, and Mac scheduling into one dashboard.

---

## Screenshots

### Dashboard Overview

![Dashboard Overview](screenshots/dashboard-overview.png)

### Portfolio vs Market

![Portfolio vs Market](screenshots/portfolio-vs-market.png)

### AI Summary

![AI Summary](screenshots/ai-summary.png)

### Sector Allocation

![Sector Allocation](screenshots/sector-allocation.png)

### Alerts

![Alerts](screenshots/alerts.png)

---

## Features

- Tracks a personal stock portfolio
- Tracks a separate stock watchlist
- Pulls stock data using `yfinance`
- Creates interactive charts using Plotly
- Generates AI portfolio summaries using Ollama/Llama 3.2
- Shows recent stock news for portfolio and watchlist stocks
- Displays a moving stock ticker
- Shows portfolio gain/loss and allocation
- Compares portfolio performance against SPY and QQQ
- Tracks sector allocation
- Tracks dividend information
- Tracks upcoming earnings dates
- Shows watchlist movers and research signals
- Checks automatic alerts for portfolio and watchlist stocks
- Opens the dashboard automatically as an HTML report
- Supports manual running anytime
- Supports scheduled daily running on Mac
- Includes a clickable schedule changer for non-technical users
- Includes report actions such as print/save as PDF and email draft support

---

## Main Dashboard Sections

The dashboard includes:

- Quick snapshot cards
- AI summary
- Portfolio vs market comparison
- Sector allocation
- Dividend information
- Earnings dates
- Report actions
- Alerts
- Watchlist metrics
- Portfolio metrics
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
├── setup_scheduler.py
├── portfolio.csv
├── watchlist.csv
├── README.md
├── requirements.txt
├── run_dashboard.command
├── run_dashboard_scheduled.command
├── change_schedule.command
├── com.finance.dashboard.plist
├── .gitignore
├── screenshots/
├── reports/
└── venv/