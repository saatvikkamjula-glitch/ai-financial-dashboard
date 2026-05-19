import yfinance as yf
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime
from pathlib import Path

watchlist = ["NVDA", "AAPL", "MSFT", "SPY", "QQQ", "BTC-USD"]

reports_folder = Path("reports")
reports_folder.mkdir(exist_ok=True)


def clean_value(value):
    if value is None or value == "N/A" or value == "":
        return "Not Applicable"
    return value


def clean_ai_text(text):
    text = text.replace("*", "")
    text = text.replace("###", "")
    text = text.replace("##", "")
    text = text.replace("#", "")
    return text.strip()


def ask_ollama(prompt):
    url = "http://localhost:11434/api/generate"

    payload = {
        "model": "llama3.2:3b",
        "prompt": prompt,
        "stream": False
    }

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return clean_ai_text(response.json()["response"])
    except Exception as error:
        return f"AI summary could not be generated. Error: {error}"


rows = []
news_rows = []

for ticker in watchlist:
    stock = yf.Ticker(ticker)
    data = stock.history(period="5d")
    info = stock.info

    current_price = data["Close"].iloc[-1]
    previous_price = data["Close"].iloc[-2]

    daily_change = current_price - previous_price
    daily_change_pct = (daily_change / previous_price) * 100

    market_cap = info.get("marketCap")
    pe_ratio = info.get("trailingPE")
    sector = info.get("sector")
    industry = info.get("industry")
    company_name = info.get("longName")

    rows.append({
        "Ticker": ticker,
        "Company Name": clean_value(company_name),
        "Current Price": round(current_price, 2),
        "Daily Change $": round(daily_change, 2),
        "Daily Change %": round(daily_change_pct, 2),
        "Market Cap": clean_value(market_cap),
        "P/E Ratio": clean_value(pe_ratio),
        "Sector": clean_value(sector),
        "Industry": clean_value(industry)
    })

    try:
        news = stock.news[:3]

        if len(news) == 0:
            news_rows.append({
                "Ticker": ticker,
                "Headline": "No recent headlines found",
                "Publisher": "Not Applicable",
                "Link": "Not Applicable"
            })

        for article in news:
            news_rows.append({
                "Ticker": ticker,
                "Headline": clean_value(article.get("title")),
                "Publisher": clean_value(article.get("publisher")),
                "Link": clean_value(article.get("link"))
            })

    except Exception:
        news_rows.append({
            "Ticker": ticker,
            "Headline": "No recent headlines found",
            "Publisher": "Not Applicable",
            "Link": "Not Applicable"
        })


df = pd.DataFrame(rows)
news_df = pd.DataFrame(news_rows)

today = datetime.now().strftime("%Y-%m-%d")

csv_file = reports_folder / f"daily_report_{today}.csv"
news_csv_file = reports_folder / f"news_report_{today}.csv"

df.to_csv(csv_file, index=False)
news_df.to_csv(news_csv_file, index=False)

best_stock = df.loc[df["Daily Change %"].idxmax()]
worst_stock = df.loc[df["Daily Change %"].idxmin()]
average_change = round(df["Daily Change %"].mean(), 2)

market_data_text = df.to_string(index=False)
news_text = news_df.to_string(index=False)

ai_prompt = f"""
You are helping build a financial research dashboard.

Analyze this watchlist data and headlines.

Important rules:
- Do not use markdown formatting.
- Do not use asterisks.
- Do NOT give direct buy or sell advice.
- Do NOT pretend you know the exact reason a stock moved unless the data clearly supports it.
- Give possible reasons investors should research further.
- Be detailed and practical.
- Focus on company news, sector trends, valuation, earnings expectations, interest rates, AI demand, macro conditions, and risk factors.
- Explain what the best and worst performers might mean.
- Include research questions someone could investigate next.

Market data:
{market_data_text}

Headlines:
{news_text}

Write a detailed market research summary with these sections:
1. Overall Market Takeaway
2. Best Performer Analysis
3. Worst Performer Analysis
4. Key Themes To Research
5. Risk Factors
6. Questions For Further Research
"""

ai_summary = ask_ollama(ai_prompt)

df["Performance Color"] = df["Daily Change %"].apply(
    lambda x: "Gain" if x >= 0 else "Loss"
)

bar_chart = px.bar(
    df,
    x="Ticker",
    y="Daily Change %",
    color="Performance Color",
    title="Daily Stock Performance",
    color_discrete_map={
        "Gain": "#22c55e",
        "Loss": "#ef4444"
    }
)

price_data = yf.download(watchlist, period="5d")["Close"]

normalized_price_data = ((price_data / price_data.iloc[0]) - 1) * 100

line_chart = px.line(
    normalized_price_data,
    title="5-Day Percentage Trend"
)

line_chart.update_layout(
    yaxis_title="Percent Change Since Start of Period",
    xaxis_title="Date"
)

ticker_items = ""

for _, row in df.iterrows():
    change_class = "positive" if row["Daily Change %"] >= 0 else "negative"

    ticker_items += f"""
    <span class="ticker-item">
        <strong>{row["Ticker"]}</strong>
        ${row["Current Price"]}
        <span class="{change_class}">
            {row["Daily Change %"]}%
        </span>
    </span>
    """

html_file = reports_folder / f"dashboard_{today}.html"

html_content = f"""
<html>
<head>
    <title>AI Financial Dashboard</title>

    <style>
        body {{
            margin: 0;
            font-family: Arial, Helvetica, sans-serif;
            background-color: #f4f6f8;
            color: #222;
        }}

        .header {{
            background-color: #111827;
            color: white;
            padding: 30px;
            text-align: center;
        }}

        .header h1 {{
            margin: 0;
            font-size: 36px;
        }}

        .header p {{
            margin-top: 10px;
            color: #d1d5db;
        }}

        .ticker-wrap {{
            width: 100%;
            overflow: hidden;
            background-color: #020617;
            color: white;
            padding: 12px 0;
            white-space: nowrap;
            box-sizing: border-box;
        }}

        .ticker {{
            display: inline-block;
            padding-left: 100%;
            animation: ticker-scroll 30s linear infinite;
        }}

        .ticker-item {{
            display: inline-block;
            margin-right: 45px;
            font-size: 16px;
        }}

        @keyframes ticker-scroll {{
            0% {{
                transform: translateX(0);
            }}
            100% {{
                transform: translateX(-100%);
            }}
        }}

        .positive {{
            color: #22c55e;
            font-weight: bold;
        }}

        .negative {{
            color: #ef4444;
            font-weight: bold;
        }}

        .container {{
            width: 90%;
            max-width: 1200px;
            margin: 30px auto;
        }}

        .card {{
            background-color: white;
            border-radius: 14px;
            padding: 24px;
            margin-bottom: 25px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.07);
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
        }}

        .stat-card {{
            background-color: #f9fafb;
            border-left: 5px solid #2563eb;
            padding: 18px;
            border-radius: 10px;
        }}

        .stat-card h3 {{
            margin: 0 0 8px 0;
            color: #374151;
        }}

        .stat-card p {{
            margin: 0;
            font-size: 22px;
            font-weight: bold;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }}

        th {{
            background-color: #111827;
            color: white;
            padding: 12px;
            text-align: left;
        }}

        td {{
            padding: 10px;
            border-bottom: 1px solid #e5e7eb;
        }}

        tr:hover {{
            background-color: #f3f4f6;
        }}

        pre {{
            white-space: pre-wrap;
            line-height: 1.6;
            font-family: Arial, Helvetica, sans-serif;
            background-color: #f9fafb;
            padding: 20px;
            border-radius: 10px;
            border-left: 5px solid #2563eb;
        }}

        .note {{
            color: #6b7280;
            font-size: 14px;
        }}
    </style>
</head>

<body>
    <div class="header">
        <h1>AI Financial Dashboard</h1>
        <p>Generated on {datetime.now().strftime("%Y-%m-%d %I:%M %p")}</p>
    </div>

    <div class="ticker-wrap">
        <div class="ticker">
            {ticker_items}
            {ticker_items}
        </div>
    </div>

    <div class="container">

        <div class="card">
            <h2>Quick Market Stats</h2>

            <div class="stats-grid">
                <div class="stat-card">
                    <h3>Best Performer</h3>
                    <p>{best_stock["Ticker"]} ({best_stock["Daily Change %"]}%)</p>
                </div>

                <div class="stat-card">
                    <h3>Worst Performer</h3>
                    <p>{worst_stock["Ticker"]} ({worst_stock["Daily Change %"]}%)</p>
                </div>

                <div class="stat-card">
                    <h3>Average Watchlist Change</h3>
                    <p>{average_change}%</p>
                </div>
            </div>
        </div>

        <div class="card">
            <h2>AI Market Research Summary</h2>
            <pre>{ai_summary}</pre>
        </div>

        <div class="card">
            <h2>Market Watchlist</h2>
            <p class="note">Some fields may show Not Applicable for ETFs, indexes, or crypto because those assets do not always have company-style metrics like sector, industry, or P/E ratio.</p>
            {df.drop(columns=["Performance Color"]).to_html(index=False)}
        </div>

        <div class="card">
            <h2>Daily Performance Chart</h2>
            {bar_chart.to_html(full_html=False)}
        </div>

        <div class="card">
            <h2>5-Day Percentage Trend</h2>
            <p class="note">This chart uses percentage change instead of raw price, so stocks, ETFs, and crypto can be compared on the same scale.</p>
            {line_chart.to_html(full_html=False)}
        </div>

        <div class="card">
            <h2>Latest Headlines</h2>
            {news_df.to_html(index=False)}
        </div>

    </div>
</body>
</html>
"""

with open(html_file, "w") as file:
    file.write(html_content)

print("\nAI Financial Dashboard Report")
print(df.drop(columns=["Performance Color"]))

print("\nAI Market Research Summary")
print(ai_summary)

print(f"\nCSV report saved to: {csv_file}")
print(f"News report saved to: {news_csv_file}")
print(f"HTML dashboard saved to: {html_file}")