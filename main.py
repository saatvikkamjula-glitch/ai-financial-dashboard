import math
import platform
import re
import subprocess
import webbrowser
from datetime import datetime
from html import escape
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import yfinance as yf


# ============================================================
# FILE SETTINGS
# ============================================================

PORTFOLIO_FILE = Path("portfolio.csv")
REPORTS_FOLDER = Path("reports")
REPORT_FILE = REPORTS_FOLDER / "financial_dashboard.html"


# ============================================================
# PORTFOLIO INPUT
# ============================================================

def ask_yes_no(question):
    while True:
        answer = input(question + " (y/n): ").strip().lower()

        if answer in ["y", "yes"]:
            return True

        if answer in ["n", "no"]:
            return False

        print("Please type y or n.")


def create_portfolio_from_terminal():
    print("\nEnter your portfolio.")
    print("Example tickers: AAPL, MSFT, NVDA, TSLA, SPY")
    print("When you are done, press Enter without typing a ticker.\n")

    holdings = []

    while True:
        ticker = input("Stock ticker: ").strip().upper()

        if ticker == "":
            break

        try:
            shares = float(input(f"How many shares of {ticker} do you own? ").strip())
            average_cost = float(input(f"What is your average cost per share for {ticker}? ").strip())
        except ValueError:
            print("Invalid number. Try that stock again.\n")
            continue

        if shares <= 0:
            print("Shares must be greater than 0.\n")
            continue

        holdings.append({
            "Ticker": ticker,
            "Shares": shares,
            "Average Cost": average_cost,
        })

        print(f"Added {ticker}.\n")

    if not holdings:
        print("No holdings entered. Creating sample portfolio instead.")

        holdings = [
            {"Ticker": "AAPL", "Shares": 2, "Average Cost": 180},
            {"Ticker": "MSFT", "Shares": 1, "Average Cost": 400},
            {"Ticker": "NVDA", "Shares": 1, "Average Cost": 900},
            {"Ticker": "TSLA", "Shares": 1, "Average Cost": 250},
            {"Ticker": "SPY", "Shares": 1, "Average Cost": 500},
        ]

    df = pd.DataFrame(holdings)
    df.to_csv(PORTFOLIO_FILE, index=False)

    print(f"\nSaved portfolio to {PORTFOLIO_FILE}.\n")

    return df


def load_portfolio():
    if PORTFOLIO_FILE.exists():
        use_existing = ask_yes_no("Do you want to use your existing portfolio.csv?")

        if use_existing:
            df = pd.read_csv(PORTFOLIO_FILE)
        else:
            df = create_portfolio_from_terminal()
    else:
        print("portfolio.csv was not found.")
        df = create_portfolio_from_terminal()

    required_columns = {"Ticker", "Shares", "Average Cost"}

    if not required_columns.issubset(df.columns):
        raise ValueError("portfolio.csv must have these columns: Ticker, Shares, Average Cost")

    df["Ticker"] = df["Ticker"].astype(str).str.upper().str.strip()
    df["Shares"] = pd.to_numeric(df["Shares"], errors="coerce").fillna(0)
    df["Average Cost"] = pd.to_numeric(df["Average Cost"], errors="coerce").fillna(0)

    df = df[df["Ticker"] != ""]
    df = df[df["Shares"] > 0]

    if df.empty:
        raise ValueError("No valid portfolio holdings found.")

    return df


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def send_mac_notification(title, message):
    if platform.system() == "Darwin":
        try:
            subprocess.run([
                "osascript",
                "-e",
                f'display notification "{message}" with title "{title}"'
            ])
        except Exception:
            print(f"{title}: {message}")
    else:
        print(f"{title}: {message}")


def clean_ai_text(text):
    if not text:
        return ""

    ansi_escape_pattern = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    text = ansi_escape_pattern.sub("", text)

    text = re.sub(r"\[[0-9;?]*[A-Za-z]", "", text)
    text = text.replace("*", "")
    text = text.replace("#", "")
    text = text.replace("`", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def format_ai_summary_as_html(text):
    text = clean_ai_text(text)

    if not text:
        return "<p>No AI summary was generated.</p>"

    lines = [line.strip() for line in text.splitlines() if line.strip()]

    html_parts = []
    bullet_items = []

    for line in lines:
        clean_line = line.strip()

        clean_line = re.sub(r"^[-•]\s*", "", clean_line)
        clean_line = re.sub(r"^\d+\.\s*", "", clean_line)

        lower_line = clean_line.lower()
        is_heading = (
            clean_line.endswith(":")
            or lower_line in [
                "portfolio summary",
                "best performer",
                "worst performer",
                "total gain or loss",
                "risk and trend notes",
                "market and stock news",
                "beginner takeaway",
                "things to watch"
            ]
        )

        if is_heading:
            if bullet_items:
                html_parts.append("<ul>" + "".join(bullet_items) + "</ul>")
                bullet_items = []

            html_parts.append(f"<h3>{escape(clean_line.rstrip(':'))}</h3>")
        else:
            bullet_items.append(f"<li>{escape(clean_line)}</li>")

    if bullet_items:
        html_parts.append("<ul>" + "".join(bullet_items) + "</ul>")

    return "\n".join(html_parts)


def safe_float(value):
    try:
        if value is None:
            return None

        value = float(value)

        if math.isnan(value):
            return None

        return value
    except Exception:
        return None


def format_money(value):
    if value is None or pd.isna(value):
        return "N/A"

    return f"${value:,.2f}"


def format_percent(value):
    if value is None or pd.isna(value):
        return "N/A"

    return f"{value:.2f}%"


def get_positive_negative_class(value):
    if value is None or pd.isna(value):
        return ""

    return "positive" if value >= 0 else "negative"


def get_sign(value):
    if value is None or pd.isna(value):
        return ""

    return "+" if value >= 0 else ""


def get_company_name(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        return info.get("shortName") or info.get("longName") or ticker
    except Exception:
        return ticker


def get_fast_info_value(stock, key):
    try:
        value = stock.fast_info.get(key)
        return safe_float(value)
    except Exception:
        return None


def calculate_rsi(prices, period=14):
    delta = prices.diff()

    gains = delta.where(delta > 0, 0)
    losses = -delta.where(delta < 0, 0)

    avg_gain = gains.rolling(window=period).mean()
    avg_loss = losses.rolling(window=period).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    if rsi.dropna().empty:
        return None

    return safe_float(rsi.iloc[-1])


def calculate_period_return(history, days):
    if len(history) <= days:
        return None

    current = history["Close"].iloc[-1]
    past = history["Close"].iloc[-days]

    if past == 0:
        return None

    return safe_float(((current - past) / past) * 100)


def get_rsi_signal(rsi):
    if rsi is None:
        return "Not enough data"

    if rsi >= 70:
        return "Overbought"

    if rsi <= 30:
        return "Oversold"

    return "Neutral"


def get_trend_signal(current_price, sma_20, sma_50):
    if sma_20 is None or sma_50 is None:
        return "Not enough data"

    if current_price > sma_20 and sma_20 > sma_50:
        return "Bullish trend"

    if current_price < sma_20 and sma_20 < sma_50:
        return "Bearish trend"

    return "Mixed trend"


# ============================================================
# STOCK DATA
# ============================================================

def get_stock_data(ticker):
    try:
        stock = yf.Ticker(ticker)

        history = stock.history(period="6mo", interval="1d")

        if history.empty or len(history) < 2:
            return None

        history = history.dropna()

        latest_close = safe_float(history["Close"].iloc[-1])
        previous_close = safe_float(history["Close"].iloc[-2])

        last_price = get_fast_info_value(stock, "last_price")
        previous_close_fast = get_fast_info_value(stock, "previous_close")
        year_high = get_fast_info_value(stock, "year_high")
        year_low = get_fast_info_value(stock, "year_low")
        market_cap = get_fast_info_value(stock, "market_cap")

        current_price = last_price if last_price is not None else latest_close
        previous_price = previous_close_fast if previous_close_fast is not None else previous_close

        daily_change = current_price - previous_price
        daily_change_percent = (daily_change / previous_price) * 100 if previous_price else 0

        sma_20 = safe_float(history["Close"].rolling(window=20).mean().iloc[-1]) if len(history) >= 20 else None
        sma_50 = safe_float(history["Close"].rolling(window=50).mean().iloc[-1]) if len(history) >= 50 else None

        rsi = calculate_rsi(history["Close"])

        daily_returns = history["Close"].pct_change().dropna()
        annualized_volatility = safe_float(daily_returns.std() * math.sqrt(252) * 100) if not daily_returns.empty else None

        five_day_return = calculate_period_return(history, 5)
        one_month_return = calculate_period_return(history, 21)
        three_month_return = calculate_period_return(history, 63)

        distance_from_52w_high = None

        if year_high is not None and year_high != 0:
            distance_from_52w_high = ((current_price - year_high) / year_high) * 100

        return {
            "ticker": ticker,
            "company_name": get_company_name(ticker),
            "history": history,
            "current_price": current_price,
            "previous_price": previous_price,
            "daily_change": daily_change,
            "daily_change_percent": daily_change_percent,
            "sma_20": sma_20,
            "sma_50": sma_50,
            "rsi": rsi,
            "rsi_signal": get_rsi_signal(rsi),
            "trend_signal": get_trend_signal(current_price, sma_20, sma_50),
            "annualized_volatility": annualized_volatility,
            "five_day_return": five_day_return,
            "one_month_return": one_month_return,
            "three_month_return": three_month_return,
            "year_high": year_high,
            "year_low": year_low,
            "distance_from_52w_high": distance_from_52w_high,
            "market_cap": market_cap,
        }

    except Exception as error:
        print(f"Error getting data for {ticker}: {error}")
        return None


def build_portfolio_dataframe(portfolio_input):
    rows = []

    for _, holding in portfolio_input.iterrows():
        ticker = holding["Ticker"]
        shares = float(holding["Shares"])
        average_cost = float(holding["Average Cost"])

        data = get_stock_data(ticker)

        if data is None:
            print(f"Could not get data for {ticker}")
            continue

        current_value = data["current_price"] * shares
        previous_value = data["previous_price"] * shares
        daily_gain_loss = current_value - previous_value

        cost_basis = average_cost * shares
        total_gain_loss = current_value - cost_basis if average_cost > 0 else None
        total_gain_loss_percent = (total_gain_loss / cost_basis) * 100 if cost_basis > 0 else None

        rows.append({
            "Ticker": ticker,
            "Company": data["company_name"],
            "Shares": shares,
            "Average Cost": average_cost,
            "Current Price": round(data["current_price"], 2),
            "Previous Price": round(data["previous_price"], 2),
            "Daily Change": round(data["daily_change"], 2),
            "Daily Change %": round(data["daily_change_percent"], 2),
            "Current Value": round(current_value, 2),
            "Previous Value": round(previous_value, 2),
            "Daily Gain/Loss": round(daily_gain_loss, 2),
            "Cost Basis": round(cost_basis, 2),
            "Total Gain/Loss": round(total_gain_loss, 2) if total_gain_loss is not None else None,
            "Total Gain/Loss %": round(total_gain_loss_percent, 2) if total_gain_loss_percent is not None else None,
            "5D Return %": round(data["five_day_return"], 2) if data["five_day_return"] is not None else None,
            "1M Return %": round(data["one_month_return"], 2) if data["one_month_return"] is not None else None,
            "3M Return %": round(data["three_month_return"], 2) if data["three_month_return"] is not None else None,
            "20D SMA": round(data["sma_20"], 2) if data["sma_20"] is not None else None,
            "50D SMA": round(data["sma_50"], 2) if data["sma_50"] is not None else None,
            "RSI": round(data["rsi"], 2) if data["rsi"] is not None else None,
            "RSI Signal": data["rsi_signal"],
            "Trend Signal": data["trend_signal"],
            "Annualized Volatility %": round(data["annualized_volatility"], 2) if data["annualized_volatility"] is not None else None,
            "52W High": round(data["year_high"], 2) if data["year_high"] is not None else None,
            "52W Low": round(data["year_low"], 2) if data["year_low"] is not None else None,
            "Distance From 52W High %": round(data["distance_from_52w_high"], 2) if data["distance_from_52w_high"] is not None else None,
            "Market Cap": data["market_cap"],
        })

    df = pd.DataFrame(rows)

    if df.empty:
        return df

    total_value = df["Current Value"].sum()
    df["Portfolio Weight %"] = (df["Current Value"] / total_value * 100).round(2)

    return df


# ============================================================
# NEWS FUNCTIONS
# ============================================================

# ============================================================
# NEWS FUNCTIONS
# ============================================================

def get_nested_value(dictionary, keys, default=None):
    """
    Safely gets a nested value from a dictionary.

    Example:
    get_nested_value(article, ["content", "title"])
    """
    current = dictionary

    for key in keys:
        if not isinstance(current, dict):
            return default

        current = current.get(key)

        if current is None:
            return default

    return current


def extract_news_article(article, ticker):
    """
    Handles multiple yfinance/Yahoo Finance news formats.

    Some yfinance versions return:
    article["title"]
    article["publisher"]
    article["link"]

    Other versions return nested data like:
    article["content"]["title"]
    article["content"]["provider"]["displayName"]
    article["content"]["canonicalUrl"]["url"]
    """

    title = (
        article.get("title")
        or get_nested_value(article, ["content", "title"])
        or get_nested_value(article, ["content", "headline"])
        or "No title available"
    )

    publisher = (
        article.get("publisher")
        or get_nested_value(article, ["content", "provider", "displayName"])
        or get_nested_value(article, ["content", "provider", "name"])
        or article.get("provider")
        or "Unknown source"
    )

    link = (
        article.get("link")
        or get_nested_value(article, ["content", "canonicalUrl", "url"])
        or get_nested_value(article, ["content", "clickThroughUrl", "url"])
        or get_nested_value(article, ["content", "previewUrl"])
        or ""
    )

    publish_time = (
        article.get("providerPublishTime")
        or article.get("pubDate")
        or get_nested_value(article, ["content", "pubDate"])
        or get_nested_value(article, ["content", "displayTime"])
    )

    date_text = "Recent"

    if publish_time:
        try:
            if isinstance(publish_time, (int, float)):
                date_text = datetime.fromtimestamp(publish_time).strftime("%b %d, %Y")
            else:
                date_text = str(publish_time)[:10]
        except Exception:
            date_text = "Recent"

    title = str(title).strip()
    publisher = str(publisher).strip()
    link = str(link).strip()

    if not title or title.lower() in ["none", "null"]:
        title = "No title available"

    if not publisher or publisher.lower() in ["none", "null"]:
        publisher = "Unknown source"

    return {
        "Ticker": ticker,
        "Title": title,
        "Publisher": publisher,
        "Date": date_text,
        "Link": link,
    }


def get_stock_news(tickers, max_articles_per_ticker=3):
    """
    Pulls recent news from yfinance for each stock.
    Handles both old and newer yfinance news formats.
    """
    news_items = []

    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            articles = stock.news or []

            count = 0

            for article in articles:
                if count >= max_articles_per_ticker:
                    break

                extracted = extract_news_article(article, ticker)

                # Skip completely useless empty articles
                if (
                    extracted["Title"] == "No title available"
                    and extracted["Publisher"] == "Unknown source"
                ):
                    continue

                news_items.append(extracted)
                count += 1

        except Exception as error:
            print(f"Could not get news for {ticker}: {error}")

    return news_items


def create_news_html(news_items):
    if not news_items:
        return """
        <div class="news-empty">
            No recent stock news was found from yfinance for these tickers.
        </div>
        """

    cards = ""

    for item in news_items:
        ticker = escape(str(item["Ticker"]))
        title = escape(str(item["Title"]))
        publisher = escape(str(item["Publisher"]))
        date_text = escape(str(item["Date"]))
        link = escape(str(item["Link"]))

        if link:
            title_html = f'<a href="{link}" target="_blank">{title}</a>'
        else:
            title_html = title

        cards += f"""
        <div class="news-card">
            <div class="news-ticker">{ticker}</div>
            <div class="news-title">{title_html}</div>
            <div class="news-meta">{publisher} • {date_text}</div>
        </div>
        """

    return f"""
    <div class="news-grid">
        {cards}
    </div>
    """


def news_items_to_text(news_items, max_items=10):
    if not news_items:
        return "No recent stock news found."

    lines = []

    for item in news_items[:max_items]:
        lines.append(
            f'{item["Ticker"]}: {item["Title"]} from {item["Publisher"]} on {item["Date"]}'
        )

    return "\n".join(lines)

# ============================================================
# CHARTS
# ============================================================

def create_portfolio_value_chart(df):
    fig = px.bar(
        df,
        x="Ticker",
        y="Current Value",
        title="Portfolio Value by Stock",
        text="Current Value",
        color="Ticker"
    )

    fig.update_traces(texttemplate="$%{text:.2f}", textposition="outside")

    fig.update_layout(
        xaxis_title="Stock",
        yaxis_title="Current Value",
        template="plotly_white",
        showlegend=False
    )

    return fig.to_html(full_html=False, include_plotlyjs="cdn")


def create_daily_gain_loss_chart(df):
    colors = ["green" if value >= 0 else "red" for value in df["Daily Gain/Loss"]]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df["Ticker"],
        y=df["Daily Gain/Loss"],
        text=[f"${value:.2f}" for value in df["Daily Gain/Loss"]],
        textposition="outside",
        marker_color=colors
    ))

    fig.update_layout(
        title="Daily Gain/Loss by Stock",
        xaxis_title="Stock",
        yaxis_title="Gain/Loss",
        template="plotly_white"
    )

    return fig.to_html(full_html=False, include_plotlyjs=False)


def create_total_gain_loss_chart(df):
    colors = ["green" if value >= 0 else "red" for value in df["Total Gain/Loss"]]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df["Ticker"],
        y=df["Total Gain/Loss"],
        text=[f"${value:.2f}" for value in df["Total Gain/Loss"]],
        textposition="outside",
        marker_color=colors
    ))

    fig.update_layout(
        title="Total Gain/Loss Compared to Average Cost",
        xaxis_title="Stock",
        yaxis_title="Total Gain/Loss",
        template="plotly_white"
    )

    return fig.to_html(full_html=False, include_plotlyjs=False)


def create_allocation_chart(df):
    fig = px.pie(
        df,
        names="Ticker",
        values="Current Value",
        title="Portfolio Allocation"
    )

    fig.update_traces(textposition="inside", textinfo="percent+label")

    fig.update_layout(template="plotly_white")

    return fig.to_html(full_html=False, include_plotlyjs=False)


def create_normalized_performance_chart(tickers):
    fig = go.Figure()

    for ticker in tickers:
        data = get_stock_data(ticker)

        if data is None:
            continue

        history = data["history"]
        normalized = history["Close"] / history["Close"].iloc[0] * 100

        fig.add_trace(go.Scatter(
            x=history.index,
            y=normalized,
            mode="lines",
            name=ticker
        ))

    fig.update_layout(
        title="6-Month Normalized Performance",
        xaxis_title="Date",
        yaxis_title="Starting at 100",
        template="plotly_white"
    )

    return fig.to_html(full_html=False, include_plotlyjs=False)


def create_moving_average_chart(tickers):
    fig = go.Figure()

    for ticker in tickers:
        data = get_stock_data(ticker)

        if data is None:
            continue

        history = data["history"].copy()
        history["SMA 20"] = history["Close"].rolling(window=20).mean()
        history["SMA 50"] = history["Close"].rolling(window=50).mean()

        fig.add_trace(go.Scatter(
            x=history.index,
            y=history["Close"],
            mode="lines",
            name=f"{ticker} Price"
        ))

        fig.add_trace(go.Scatter(
            x=history.index,
            y=history["SMA 20"],
            mode="lines",
            name=f"{ticker} 20D SMA",
            line=dict(dash="dash")
        ))

        fig.add_trace(go.Scatter(
            x=history.index,
            y=history["SMA 50"],
            mode="lines",
            name=f"{ticker} 50D SMA",
            line=dict(dash="dot")
        ))

    fig.update_layout(
        title="Price With Moving Averages",
        xaxis_title="Date",
        yaxis_title="Price",
        template="plotly_white"
    )

    return fig.to_html(full_html=False, include_plotlyjs=False)


def create_volatility_chart(df):
    fig = px.bar(
        df,
        x="Ticker",
        y="Annualized Volatility %",
        title="Annualized Volatility",
        text="Annualized Volatility %",
        color="Annualized Volatility %",
        color_continuous_scale="Reds"
    )

    fig.update_traces(texttemplate="%{text:.2f}%", textposition="outside")

    fig.update_layout(
        xaxis_title="Stock",
        yaxis_title="Volatility",
        template="plotly_white",
        showlegend=False
    )

    return fig.to_html(full_html=False, include_plotlyjs=False)


# ============================================================
# AI SUMMARY
# ============================================================

def generate_ai_summary(df, news_items):
    total_value = df["Current Value"].sum()
    previous_value = df["Previous Value"].sum()
    total_daily_gain_loss = df["Daily Gain/Loss"].sum()
    total_daily_percent = (total_daily_gain_loss / previous_value) * 100 if previous_value != 0 else 0

    total_cost_basis = df["Cost Basis"].sum()
    total_unrealized_gain_loss = df["Total Gain/Loss"].sum()
    total_unrealized_percent = (total_unrealized_gain_loss / total_cost_basis) * 100 if total_cost_basis > 0 else 0

    best_stock = df.loc[df["Daily Gain/Loss"].idxmax()]
    worst_stock = df.loc[df["Daily Gain/Loss"].idxmin()]
    largest_position = df.loc[df["Portfolio Weight %"].idxmax()]

    news_text = news_items_to_text(news_items)

    prompt = f"""
You are an AI financial dashboard assistant.

Formatting rules:
Do not use markdown.
Do not use asterisks.
Do not use hashtags.
Do not use code blocks.
Use plain sentences only.
Keep every point short.
Do not give official financial advice.

Portfolio data:
{df.to_string(index=False)}

Recent stock news:
{news_text}

Write this exact structure:

Portfolio Summary:
- Explain today's total portfolio movement.
- Mention the total portfolio value.
- Mention daily gain or loss.

Best Performer:
- Explain which stock helped the most today and why.

Worst Performer:
- Explain which stock hurt the most today and why.

Total Gain or Loss:
- Explain the total gain or loss compared to average cost.

Risk and Trend Notes:
- Mention RSI, moving averages, volatility, and allocation.
- Mention if the portfolio depends heavily on one stock.

Market and Stock News:
- Summarize the most important news items.
- Explain which news may matter to the portfolio.
- If the news is not clearly connected to a price move, say that clearly.

Beginner Takeaway:
- Give one simple takeaway.
"""

    try:
        result = subprocess.run(
            ["ollama", "run", "llama3.2"],
            input=prompt,
            text=True,
            capture_output=True,
            timeout=120
        )

        if result.returncode == 0 and result.stdout.strip():
            return clean_ai_text(result.stdout.strip())

    except Exception as error:
        print(f"Ollama failed: {error}")

    backup = f"""
Portfolio Summary:
Your portfolio is worth {format_money(total_value)}.
Your daily gain or loss is {get_sign(total_daily_gain_loss)}{format_money(total_daily_gain_loss)}, which is {get_sign(total_daily_percent)}{format_percent(total_daily_percent)} today.

Best Performer:
The best performer today is {best_stock["Ticker"]}, with a daily impact of {format_money(best_stock["Daily Gain/Loss"])}.

Worst Performer:
The worst performer today is {worst_stock["Ticker"]}, with a daily impact of {format_money(worst_stock["Daily Gain/Loss"])}.

Total Gain or Loss:
Your total gain or loss compared to average cost is {get_sign(total_unrealized_gain_loss)}{format_money(total_unrealized_gain_loss)}, which is {get_sign(total_unrealized_percent)}{format_percent(total_unrealized_percent)}.

Risk and Trend Notes:
Your largest position is {largest_position["Ticker"]}, which is {format_percent(largest_position["Portfolio Weight %"])} of your portfolio.
Watch allocation, moving averages, RSI, volatility, and whether too much of the portfolio depends on one stock.

Market and Stock News:
The dashboard found {len(news_items)} recent stock news items from yfinance.
Read the news cards below to see what may have affected your holdings.

Beginner Takeaway:
Do not only look at daily gains and losses. Also watch news, long-term trend, risk, and portfolio concentration.
"""

    return clean_ai_text(backup)


# ============================================================
# HTML REPORT
# ============================================================

def create_moving_ticker(df):
    ticker_items = ""

    for _, row in df.iterrows():
        change_class = get_positive_negative_class(row["Daily Change %"])
        sign = get_sign(row["Daily Change %"])

        ticker_items += f"""
        <div class="ticker-item">
            <div class="ticker-symbol">{escape(str(row["Ticker"]))}</div>
            <div class="ticker-company">{escape(str(row["Company"]))}</div>
            <div class="ticker-price">{format_money(row["Current Price"])}</div>
            <div class="{change_class}">{sign}{format_percent(row["Daily Change %"])}</div>
        </div>
        """

    return ticker_items + ticker_items


def create_table_html(df):
    rows = ""

    for _, row in df.iterrows():
        daily_class = get_positive_negative_class(row["Daily Gain/Loss"])
        daily_percent_class = get_positive_negative_class(row["Daily Change %"])
        total_class = get_positive_negative_class(row["Total Gain/Loss"])
        total_percent_class = get_positive_negative_class(row["Total Gain/Loss %"])

        rows += f"""
        <tr>
            <td><strong>{escape(str(row["Ticker"]))}</strong></td>
            <td>{escape(str(row["Company"]))}</td>
            <td>{row["Shares"]:.4g}</td>
            <td>{format_money(row["Average Cost"])}</td>
            <td>{format_money(row["Current Price"])}</td>
            <td class="{daily_percent_class}">{get_sign(row["Daily Change %"])}{format_percent(row["Daily Change %"])}</td>
            <td class="{daily_class}">{get_sign(row["Daily Gain/Loss"])}{format_money(row["Daily Gain/Loss"])}</td>
            <td>{format_money(row["Current Value"])}</td>
            <td>{format_percent(row["Portfolio Weight %"])}</td>
            <td>{format_money(row["Cost Basis"])}</td>
            <td class="{total_class}">{get_sign(row["Total Gain/Loss"])}{format_money(row["Total Gain/Loss"])}</td>
            <td class="{total_percent_class}">{get_sign(row["Total Gain/Loss %"])}{format_percent(row["Total Gain/Loss %"])}</td>
            <td>{format_percent(row["5D Return %"])}</td>
            <td>{format_percent(row["1M Return %"])}</td>
            <td>{format_percent(row["3M Return %"])}</td>
            <td>{row["RSI"] if pd.notna(row["RSI"]) else "N/A"}</td>
            <td>{escape(str(row["RSI Signal"]))}</td>
            <td>{escape(str(row["Trend Signal"]))}</td>
            <td>{format_percent(row["Annualized Volatility %"])}</td>
            <td>{format_money(row["52W High"])}</td>
            <td>{format_money(row["52W Low"])}</td>
            <td>{format_percent(row["Distance From 52W High %"])}</td>
        </tr>
        """

    return f"""
    <table class="portfolio-table">
        <thead>
            <tr>
                <th>Ticker</th>
                <th>Company</th>
                <th>Shares</th>
                <th>Avg Cost</th>
                <th>Price</th>
                <th>Daily %</th>
                <th>Daily $</th>
                <th>Value</th>
                <th>Weight</th>
                <th>Cost Basis</th>
                <th>Total $</th>
                <th>Total %</th>
                <th>5D</th>
                <th>1M</th>
                <th>3M</th>
                <th>RSI</th>
                <th>RSI Signal</th>
                <th>Trend</th>
                <th>Volatility</th>
                <th>52W High</th>
                <th>52W Low</th>
                <th>From 52W High</th>
            </tr>
        </thead>
        <tbody>
            {rows}
        </tbody>
    </table>
    """


def create_html_report(df, ai_summary, news_items):
    REPORTS_FOLDER.mkdir(exist_ok=True)

    tickers = df["Ticker"].tolist()

    total_value = df["Current Value"].sum()
    previous_value = df["Previous Value"].sum()
    total_daily_gain_loss = df["Daily Gain/Loss"].sum()
    total_daily_percent = (total_daily_gain_loss / previous_value) * 100 if previous_value != 0 else 0

    total_cost_basis = df["Cost Basis"].sum()
    total_gain_loss = df["Total Gain/Loss"].sum()
    total_gain_loss_percent = (total_gain_loss / total_cost_basis) * 100 if total_cost_basis > 0 else 0

    best_stock = df.loc[df["Daily Gain/Loss"].idxmax()]
    worst_stock = df.loc[df["Daily Gain/Loss"].idxmin()]
    largest_position = df.loc[df["Portfolio Weight %"].idxmax()]

    ticker_html = create_moving_ticker(df)
    table_html = create_table_html(df)
    ai_summary_html = format_ai_summary_as_html(ai_summary)
    news_html = create_news_html(news_items)

    portfolio_value_chart = create_portfolio_value_chart(df)
    daily_gain_loss_chart = create_daily_gain_loss_chart(df)
    total_gain_loss_chart = create_total_gain_loss_chart(df)
    allocation_chart = create_allocation_chart(df)
    normalized_chart = create_normalized_performance_chart(tickers)
    moving_average_chart = create_moving_average_chart(tickers)
    volatility_chart = create_volatility_chart(df)

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>AI Financial Dashboard</title>

    <style>
        body {{
            font-family: Arial, sans-serif;
            background: #f4f6f8;
            color: #222;
            margin: 0;
            padding: 0;
        }}

        .container {{
            max-width: 1300px;
            margin: auto;
            padding: 30px;
        }}

        h1 {{
            text-align: center;
            margin-bottom: 5px;
        }}

        .subtitle {{
            text-align: center;
            color: #666;
            margin-bottom: 25px;
        }}

        .ticker-wrapper {{
            overflow: hidden;
            background: #111827;
            padding: 15px;
            border-radius: 18px;
            margin-bottom: 25px;
            box-shadow: 0 4px 16px rgba(0,0,0,0.18);
        }}

        .ticker-track {{
            display: flex;
            gap: 15px;
            width: max-content;
            animation: tickerMove 25s linear infinite;
        }}

        .ticker-wrapper:hover .ticker-track {{
            animation-play-state: paused;
        }}

        @keyframes tickerMove {{
            from {{
                transform: translateX(0);
            }}
            to {{
                transform: translateX(-50%);
            }}
        }}

        .ticker-item {{
            min-width: 180px;
            background: #1f2937;
            color: white;
            padding: 14px;
            border-radius: 14px;
            text-align: center;
            flex-shrink: 0;
        }}

        .ticker-symbol {{
            font-size: 22px;
            font-weight: bold;
        }}

        .ticker-company {{
            font-size: 12px;
            color: #d1d5db;
            margin-top: 4px;
            height: 16px;
            overflow: hidden;
        }}

        .ticker-price {{
            font-size: 17px;
            margin-top: 6px;
        }}

        .cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}

        .card {{
            background: white;
            padding: 22px;
            border-radius: 16px;
            box-shadow: 0 4px 14px rgba(0,0,0,0.08);
        }}

        .card h2 {{
            margin-top: 0;
            color: #555;
            font-size: 17px;
        }}

        .value {{
            font-size: 28px;
            font-weight: bold;
        }}

        .small-note {{
            color: #777;
            font-size: 14px;
            margin-top: 8px;
        }}

        .positive {{
            color: green;
            font-weight: bold;
        }}

        .negative {{
            color: red;
            font-weight: bold;
        }}

        .section {{
            background: white;
            padding: 25px;
            border-radius: 16px;
            box-shadow: 0 4px 14px rgba(0,0,0,0.08);
            margin-bottom: 30px;
            overflow-x: auto;
        }}

        .ai-summary {{
            line-height: 1.6;
            background: #f9fafb;
            padding: 18px;
            border-radius: 12px;
            border-left: 5px solid #111827;
        }}

        .ai-summary h3 {{
            margin-bottom: 8px;
            margin-top: 18px;
            color: #111827;
        }}

        .ai-summary h3:first-child {{
            margin-top: 0;
        }}

        .ai-summary ul {{
            margin-top: 5px;
            margin-bottom: 12px;
            padding-left: 24px;
        }}

        .ai-summary li {{
            margin-bottom: 8px;
        }}

        .portfolio-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }}

        .portfolio-table th,
        .portfolio-table td {{
            border: 1px solid #ddd;
            padding: 9px;
            text-align: center;
            white-space: nowrap;
        }}

        .portfolio-table th {{
            background: #111827;
            color: white;
        }}

        .portfolio-table tr:nth-child(even) {{
            background: #f9fafb;
        }}

        .news-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 16px;
        }}

        .news-card {{
            background: #f9fafb;
            border: 1px solid #e5e7eb;
            border-radius: 14px;
            padding: 16px;
        }}

        .news-ticker {{
            display: inline-block;
            background: #111827;
            color: white;
            font-weight: bold;
            font-size: 13px;
            padding: 5px 9px;
            border-radius: 999px;
            margin-bottom: 10px;
        }}

        .news-title {{
            font-size: 15px;
            font-weight: bold;
            line-height: 1.4;
            margin-bottom: 8px;
        }}

        .news-title a {{
            color: #111827;
            text-decoration: none;
        }}

        .news-title a:hover {{
            text-decoration: underline;
        }}

        .news-meta {{
            color: #666;
            font-size: 13px;
        }}

        .news-empty {{
            background: #f9fafb;
            border: 1px solid #e5e7eb;
            border-radius: 14px;
            padding: 16px;
            color: #666;
        }}

        .footer {{
            text-align: center;
            color: #777;
            margin-top: 30px;
            font-size: 14px;
        }}
    </style>
</head>

<body>
    <div class="container">
        <h1>AI Financial Dashboard</h1>
        <p class="subtitle">Generated on {datetime.now().strftime("%B %d, %Y at %I:%M %p")}</p>

        <div class="ticker-wrapper">
            <div class="ticker-track">
                {ticker_html}
            </div>
        </div>

        <div class="cards">
            <div class="card">
                <h2>Total Portfolio Value</h2>
                <div class="value">{format_money(total_value)}</div>
                <div class="small-note">Current value of your holdings</div>
            </div>

            <div class="card">
                <h2>Daily Gain/Loss</h2>
                <div class="value {get_positive_negative_class(total_daily_gain_loss)}">
                    {get_sign(total_daily_gain_loss)}{format_money(total_daily_gain_loss)}
                </div>
                <div class="small-note">{get_sign(total_daily_percent)}{format_percent(total_daily_percent)} today</div>
            </div>

            <div class="card">
                <h2>Total Gain/Loss</h2>
                <div class="value {get_positive_negative_class(total_gain_loss)}">
                    {get_sign(total_gain_loss)}{format_money(total_gain_loss)}
                </div>
                <div class="small-note">{get_sign(total_gain_loss_percent)}{format_percent(total_gain_loss_percent)} vs average cost</div>
            </div>

            <div class="card">
                <h2>Best Performer</h2>
                <div class="value positive">{escape(str(best_stock["Ticker"]))}</div>
                <div class="small-note">{format_money(best_stock["Daily Gain/Loss"])} today</div>
            </div>

            <div class="card">
                <h2>Worst Performer</h2>
                <div class="value negative">{escape(str(worst_stock["Ticker"]))}</div>
                <div class="small-note">{format_money(worst_stock["Daily Gain/Loss"])} today</div>
            </div>

            <div class="card">
                <h2>Largest Position</h2>
                <div class="value">{escape(str(largest_position["Ticker"]))}</div>
                <div class="small-note">{format_percent(largest_position["Portfolio Weight %"])} of portfolio</div>
            </div>
        </div>

        <div class="section">
            <h2>AI Portfolio Summary</h2>
            <div class="ai-summary">
                {ai_summary_html}
            </div>
        </div>

        <div class="section">
            <h2>Recent Stock News</h2>
            {news_html}
        </div>

        <div class="section">
            <h2>Portfolio Metrics Table</h2>
            {table_html}
        </div>

        <div class="section">
            {portfolio_value_chart}
        </div>

        <div class="section">
            {daily_gain_loss_chart}
        </div>

        <div class="section">
            {total_gain_loss_chart}
        </div>

        <div class="section">
            {allocation_chart}
        </div>

        <div class="section">
            {normalized_chart}
        </div>

        <div class="section">
            {moving_average_chart}
        </div>

        <div class="section">
            {volatility_chart}
        </div>

        <p class="footer">
            Portfolio is entered in the Terminal. This dashboard is display only. Data and news are latest available from yfinance and are not professional tick-by-tick trading data. This is not financial advice.
        </p>
    </div>
</body>
</html>
"""

    with open(REPORT_FILE, "w", encoding="utf-8") as file:
        file.write(html)

    return REPORT_FILE.resolve()


def open_report(report_path):
    if report_path.exists():
        webbrowser.open(f"file://{report_path}")
        print(f"Opened report: {report_path}")
    else:
        print(f"Report not found: {report_path}")


# ============================================================
# MAIN PROGRAM
# ============================================================

def main():
    print("Building AI financial dashboard...")

    portfolio_input = load_portfolio()
    print("Portfolio input loaded.")

    df = build_portfolio_dataframe(portfolio_input)

    if df.empty:
        print("No stock data found. Check your tickers or internet connection.")
        return

    print("Portfolio data loaded.")
    print(df)

    tickers = df["Ticker"].tolist()

    print("Gathering recent stock news...")
    news_items = get_stock_news(tickers)
    print(f"Found {len(news_items)} news items.")

    ai_summary = generate_ai_summary(df, news_items)
    print("AI summary created.")

    report_path = create_html_report(df, ai_summary, news_items)
    print(f"Report saved to: {report_path}")

    open_report(report_path)

    send_mac_notification(
        "AI Financial Dashboard",
        "Your financial dashboard with news is ready."
    )


if __name__ == "__main__":
    main()