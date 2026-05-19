# AI Financial Dashboard

An AI-powered financial dashboard that tracks market data, generates charts, saves daily reports, and uses a local LLM through Ollama to produce market research summaries.

## Features

- Tracks stocks, ETFs, and crypto using Yahoo Finance data
- Displays current price, daily change, market cap, P/E ratio, sector, and industry
- Saves daily market reports as CSV files
- Saves news headline reports as CSV files
- Generates an HTML dashboard
- Includes a moving stock ticker display
- Creates daily performance and 7-day percentage trend charts
- Uses Ollama with Llama 3.2 to generate AI market research summaries
- Avoids direct buy/sell advice and focuses on research direction

## Tools Used

- Python
- yfinance
- pandas
- plotly
- requests
- Ollama
- Llama 3.2

## How To Run

1. Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate