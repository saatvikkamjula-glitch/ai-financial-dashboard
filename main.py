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
WATCHLIST_FILE = Path("watchlist.csv")
REPORTS_FOLDER = Path("reports")
REPORT_FILE = REPORTS_FOLDER / "financial_dashboard.html"


# ============================================================
# INPUT FUNCTIONS
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
    print("These are stocks you own.")
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
            try:
                df = pd.read_csv(PORTFOLIO_FILE)
            except pd.errors.EmptyDataError:
                print("portfolio.csv is empty.")
                df = create_portfolio_from_terminal()
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


def create_watchlist_from_terminal():
    print("\nEnter your watchlist.")
    print("These are stocks you want to track but do not own yet.")
    print("Example tickers: AMD, GOOGL, META, JPM, COST")
    print("When you are done, press Enter without typing a ticker.\n")

    tickers = []

    while True:
        ticker = input("Watchlist ticker: ").strip().upper()

        if ticker == "":
            break

        if ticker in tickers:
            print(f"{ticker} is already in your watchlist.\n")
            continue

        tickers.append(ticker)
        print(f"Added {ticker} to watchlist.\n")

    if not tickers:
        print("No watchlist tickers entered. Creating sample watchlist instead.")
        tickers = ["AMD", "GOOGL", "META", "JPM", "COST"]

    df = pd.DataFrame({"Ticker": tickers})
    df.to_csv(WATCHLIST_FILE, index=False)
    print(f"\nSaved watchlist to {WATCHLIST_FILE}.\n")

    return df


def load_watchlist():
    if WATCHLIST_FILE.exists():
        use_existing = ask_yes_no("Do you want to use your existing watchlist.csv?")

        if use_existing:
            try:
                df = pd.read_csv(WATCHLIST_FILE)
            except pd.errors.EmptyDataError:
                print("watchlist.csv is empty.")
                df = create_watchlist_from_terminal()
        else:
            df = create_watchlist_from_terminal()
    else:
        print("watchlist.csv was not found.")
        df = create_watchlist_from_terminal()

    if "Ticker" not in df.columns:
        raise ValueError("watchlist.csv must have one column called Ticker")

    df["Ticker"] = df["Ticker"].astype(str).str.upper().str.strip()
    df = df[df["Ticker"] != ""]
    df = df.drop_duplicates(subset=["Ticker"])

    if df.empty:
        df = create_watchlist_from_terminal()

    return df


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def send_mac_notification(title, message):
    if platform.system() == "Darwin":
        try:
            safe_title = str(title).replace('"', "'")
            safe_message = str(message).replace('"', "'")

            subprocess.run([
                "osascript",
                "-e",
                f'display notification "{safe_message}" with title "{safe_title}"'
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
    """
    Converts the AI summary into clean HTML.

    Extra polish:
    - Keeps headings separate
    - Prevents broken half-sentence bullets
    - Merges continuation lines into the previous bullet
    - Keeps every bullet readable
    """
    text = clean_ai_text(text)

    if not text:
        return "<p>No AI summary was generated.</p>"

    raw_lines = [line.strip() for line in text.splitlines() if line.strip()]

    headings = [
        "portfolio summary",
        "best performer",
        "worst performer",
        "total gain or loss",
        "portfolio vs market",
        "benchmark comparison",
        "sector allocation",
        "dividends",
        "dividend tracking",
        "earnings dates",
        "earnings tracking",
        "risk and trend notes",
        "watchlist summary",
        "watchlist movers",
        "market and stock news",
        "beginner takeaway",
    ]

    continuation_starts = (
        "from ",
        "with ",
        "and ",
        "or ",
        "but ",
        "because ",
        "while ",
        "compared ",
        "change of ",
        "average ",
        "a ",
        "an ",
        "the previous ",
    )

    html_parts = []
    bullet_items = []

    def flush_bullets():
        nonlocal bullet_items

        if bullet_items:
            html_parts.append("<ul>" + "".join(f"<li>{escape(item)}</li>" for item in bullet_items) + "</ul>")
            bullet_items = []

    def is_heading(line):
        clean = line.strip().rstrip(":")
        return clean.lower() in headings

    def normalize_heading(line):
        clean = line.strip().rstrip(":")
        return clean.title()

    def starts_as_continuation(line):
        lower_line = line.lower().strip()

        if not bullet_items:
            return False

        if lower_line.startswith(continuation_starts):
            return True

        # If the line is short and starts lowercase, it is probably a broken sentence.
        if line and line[0].islower() and len(line.split()) <= 10:
            return True

        # If the previous bullet does not end like a complete sentence, merge it.
        previous = bullet_items[-1].strip()
        if previous and previous[-1] not in ".!?":
            return True

        return False

    for line in raw_lines:
        clean_line = line.strip()

        # Remove common bullet/number prefixes.
        clean_line = re.sub(r"^[-•]\s*", "", clean_line)
        clean_line = re.sub(r"^\d+\.\s*", "", clean_line)
        clean_line = clean_line.strip()

        if not clean_line:
            continue

        if is_heading(clean_line):
            flush_bullets()
            html_parts.append(f"<h3>{escape(normalize_heading(clean_line))}</h3>")
            continue

        # Handle accidental heading-like bullets.
        if clean_line.lower().rstrip(":") in headings:
            flush_bullets()
            html_parts.append(f"<h3>{escape(normalize_heading(clean_line))}</h3>")
            continue

        if starts_as_continuation(clean_line):
            bullet_items[-1] = bullet_items[-1].rstrip() + " " + clean_line
        else:
            bullet_items.append(clean_line)

    flush_bullets()

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


def format_large_number(value):
    if value is None or pd.isna(value):
        return "N/A"

    value = float(value)

    if abs(value) >= 1_000_000_000_000:
        return f"${value / 1_000_000_000_000:.2f}T"

    if abs(value) >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B"

    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:.2f}M"

    return f"${value:,.2f}"


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


def get_research_signal(row):
    score = 0

    daily_change = row.get("Daily Change %")
    one_month = row.get("1M Return %")
    rsi = row.get("RSI")
    trend = row.get("Trend Signal")

    if pd.notna(one_month):
        if one_month > 5:
            score += 1
        elif one_month < -5:
            score -= 1

    if pd.notna(daily_change):
        if daily_change > 2:
            score += 1
        elif daily_change < -2:
            score -= 1

    if pd.notna(rsi):
        if 40 <= rsi <= 65:
            score += 1
        elif rsi >= 75:
            score -= 1

    if trend == "Bullish trend":
        score += 1
    elif trend == "Bearish trend":
        score -= 1

    if score >= 2:
        return "Strong watch"

    if score == 1:
        return "Worth watching"

    if score == 0:
        return "Neutral"

    return "Caution"


# ============================================================
# DASHBOARD ALERT FUNCTIONS
# ============================================================

def build_dashboard_alerts(portfolio_df, watchlist_df):
    alerts = []

    def check_row(row, category):
        ticker = row["Ticker"]
        daily_change = row.get("Daily Change %")
        rsi = row.get("RSI")
        distance_from_high = row.get("Distance From 52W High %")
        trend = row.get("Trend Signal")

        if pd.notna(daily_change) and abs(daily_change) >= 3:
            direction = "up" if daily_change >= 0 else "down"

            alerts.append({
                "Category": category,
                "Ticker": ticker,
                "Type": "Large Daily Move",
                "Level": "high",
                "Message": f"{ticker} is {direction} {abs(daily_change):.2f}% today."
            })

        if pd.notna(rsi) and rsi >= 70:
            alerts.append({
                "Category": category,
                "Ticker": ticker,
                "Type": "RSI Overbought",
                "Level": "medium",
                "Message": f"{ticker} has an RSI of {rsi:.2f}, which may be overbought."
            })

        if pd.notna(rsi) and rsi <= 30:
            alerts.append({
                "Category": category,
                "Ticker": ticker,
                "Type": "RSI Oversold",
                "Level": "medium",
                "Message": f"{ticker} has an RSI of {rsi:.2f}, which may be oversold."
            })

        if pd.notna(distance_from_high) and distance_from_high >= -5:
            alerts.append({
                "Category": category,
                "Ticker": ticker,
                "Type": "Near 52-Week High",
                "Level": "low",
                "Message": f"{ticker} is close to its 52-week high."
            })

        if pd.notna(distance_from_high) and distance_from_high <= -25:
            alerts.append({
                "Category": category,
                "Ticker": ticker,
                "Type": "Far From 52-Week High",
                "Level": "low",
                "Message": f"{ticker} is {distance_from_high:.2f}% below its 52-week high."
            })

        if trend == "Bearish trend":
            alerts.append({
                "Category": category,
                "Ticker": ticker,
                "Type": "Bearish Trend",
                "Level": "medium",
                "Message": f"{ticker} is showing a bearish moving-average trend."
            })

    for _, row in portfolio_df.iterrows():
        check_row(row, "Portfolio")

    if not watchlist_df.empty:
        for _, row in watchlist_df.iterrows():
            check_row(row, "Watchlist")

    return alerts


def create_alert_cards_html(alerts):
    portfolio_alerts = [alert for alert in alerts if alert["Category"] == "Portfolio"]
    watchlist_alerts = [alert for alert in alerts if alert["Category"] == "Watchlist"]

    def build_group(title, group_alerts):
        if not group_alerts:
            return f"""
            <div class="alert-group">
                <h3>{title}</h3>
                <div class="alert-empty">No alerts triggered.</div>
            </div>
            """

        cards = ""

        for alert in group_alerts:
            cards += f"""
            <div class="alert-card alert-{alert["Level"]}">
                <div class="alert-top">
                    <span class="alert-ticker">{escape(str(alert["Ticker"]))}</span>
                    <span class="alert-type">{escape(str(alert["Type"]))}</span>
                </div>
                <div class="alert-message">{escape(str(alert["Message"]))}</div>
            </div>
            """

        return f"""
        <div class="alert-group">
            <h3>{title}</h3>
            <div class="alert-grid">
                {cards}
            </div>
        </div>
        """

    return f"""
    <div class="alerts-container">
        {build_group("Portfolio Alerts", portfolio_alerts)}
        {build_group("Watchlist Alerts", watchlist_alerts)}
    </div>
    """


def wrap_section(content, title=None):
    if content is None or str(content).strip() == "":
        return ""

    heading = f"<h2>{title}</h2>" if title else ""

    return f"""
    <div class="section">
        {heading}
        {content}
    </div>
    """


# ============================================================
# STOCK DATA
# ============================================================

def format_possible_date(value):
    try:
        if value is None:
            return "N/A"

        if isinstance(value, (list, tuple)) and len(value) > 0:
            value = value[0]

        if isinstance(value, pd.Series) and not value.empty:
            value = value.iloc[0]

        if isinstance(value, pd.DataFrame) and not value.empty:
            value = value.iloc[0, 0]

        date_value = pd.to_datetime(value, errors="coerce")

        if pd.isna(date_value):
            return "N/A"

        return date_value.strftime("%b %d, %Y")
    except Exception:
        return "N/A"


def get_next_earnings_date(stock, info):
    try:
        if info.get("nextEarningsDate"):
            return format_possible_date(info.get("nextEarningsDate"))

        calendar = stock.calendar

        if isinstance(calendar, dict):
            for key in ["Earnings Date", "earningsDate"]:
                if key in calendar:
                    return format_possible_date(calendar[key])

        if isinstance(calendar, pd.DataFrame) and not calendar.empty:
            for possible_index in ["Earnings Date", "Earnings Average"]:
                if possible_index in calendar.index:
                    return format_possible_date(calendar.loc[possible_index].values[0])

            return format_possible_date(calendar.iloc[0, 0])
    except Exception:
        pass

    return "N/A"


def clean_dividend_yield(value):
    value = safe_float(value)

    if value is None:
        return None

    if value <= 1:
        return value * 100

    return value


def get_stock_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        history = stock.history(period="6mo", interval="1d")

        if history.empty or len(history) < 2:
            return None

        history = history.dropna()

        try:
            info = stock.info or {}
        except Exception:
            info = {}

        latest_close = safe_float(history["Close"].iloc[-1])
        previous_close = safe_float(history["Close"].iloc[-2])

        last_price = get_fast_info_value(stock, "last_price")
        previous_close_fast = get_fast_info_value(stock, "previous_close")
        year_high = get_fast_info_value(stock, "year_high")
        year_low = get_fast_info_value(stock, "year_low")
        market_cap = get_fast_info_value(stock, "market_cap")

        current_price = last_price if last_price is not None else latest_close
        previous_price = previous_close_fast if previous_close_fast is not None else previous_close

        if current_price is None or previous_price is None:
            return None

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

        dividend_yield = clean_dividend_yield(
            info.get("dividendYield")
            or info.get("trailingAnnualDividendYield")
            or info.get("fiveYearAvgDividendYield")
        )

        return {
            "ticker": ticker,
            "company_name": info.get("shortName") or info.get("longName") or ticker,
            "sector": info.get("sector") or "Unknown",
            "industry": info.get("industry") or "Unknown",
            "dividend_yield": dividend_yield,
            "earnings_date": get_next_earnings_date(stock, info),
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
            print(f"Could not get portfolio data for {ticker}")
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
            "Sector": data["sector"],
            "Industry": data["industry"],
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
            "Dividend Yield %": round(data["dividend_yield"], 2) if data["dividend_yield"] is not None else None,
            "Estimated Annual Dividend": round(current_value * (data["dividend_yield"] / 100), 2) if data["dividend_yield"] is not None else 0,
            "Next Earnings Date": data["earnings_date"],
        })

    df = pd.DataFrame(rows)

    if df.empty:
        return df

    total_value = df["Current Value"].sum()
    df["Portfolio Weight %"] = (df["Current Value"] / total_value * 100).round(2)

    return df


def build_watchlist_dataframe(watchlist_input):
    rows = []

    for _, item in watchlist_input.iterrows():
        ticker = item["Ticker"]
        data = get_stock_data(ticker)

        if data is None:
            print(f"Could not get watchlist data for {ticker}")
            continue

        rows.append({
            "Ticker": ticker,
            "Company": data["company_name"],
            "Sector": data["sector"],
            "Industry": data["industry"],
            "Current Price": round(data["current_price"], 2),
            "Previous Price": round(data["previous_price"], 2),
            "Daily Change": round(data["daily_change"], 2),
            "Daily Change %": round(data["daily_change_percent"], 2),
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
            "Dividend Yield %": round(data["dividend_yield"], 2) if data["dividend_yield"] is not None else None,
            "Next Earnings Date": data["earnings_date"],
        })

    df = pd.DataFrame(rows)

    if df.empty:
        return df

    df["Research Signal"] = df.apply(get_research_signal, axis=1)

    return df



# ============================================================
# SECTOR, DIVIDEND, AND EARNINGS FUNCTIONS
# ============================================================

def build_sector_allocation(portfolio_df):
    if portfolio_df.empty or "Sector" not in portfolio_df.columns:
        return pd.DataFrame()

    sector_df = (
        portfolio_df
        .groupby("Sector", dropna=False)["Current Value"]
        .sum()
        .reset_index()
        .sort_values("Current Value", ascending=False)
    )

    total_value = sector_df["Current Value"].sum()

    if total_value > 0:
        sector_df["Weight %"] = (sector_df["Current Value"] / total_value * 100).round(2)
    else:
        sector_df["Weight %"] = 0

    return sector_df


def create_sector_cards_html(sector_df):
    if sector_df.empty:
        return "<p>No sector data available.</p>"

    cards = ""

    for _, row in sector_df.iterrows():
        cards += f"""
        <div class="sector-card">
            <div class="sector-name">{escape(str(row["Sector"]))}</div>
            <div class="sector-weight">{format_percent(row["Weight %"])}</div>
            <div class="sector-value">{format_money(row["Current Value"])}</div>
        </div>
        """

    return f"""
    <div class="sector-card-grid">
        {cards}
    </div>
    """


def create_sector_pie_chart(sector_df):
    if sector_df.empty:
        return ""

    fig = px.pie(
        sector_df,
        names="Sector",
        values="Current Value",
        title="Sector Allocation"
    )

    fig.update_traces(textposition="inside", textinfo="percent+label")
    fig.update_layout(template="plotly_white")

    return fig.to_html(full_html=False, include_plotlyjs="cdn")


def create_sector_table_html(sector_df):
    if sector_df.empty:
        return "<p>No sector data available.</p>"

    rows = ""

    for _, row in sector_df.iterrows():
        rows += f"""
        <tr>
            <td><strong>{escape(str(row["Sector"]))}</strong></td>
            <td>{format_money(row["Current Value"])}</td>
            <td>{format_percent(row["Weight %"])}</td>
        </tr>
        """

    return f"""
    <table class="benchmark-table">
        <thead>
            <tr>
                <th>Sector</th>
                <th>Value</th>
                <th>Portfolio Weight</th>
            </tr>
        </thead>
        <tbody>
            {rows}
        </tbody>
    </table>
    """


def get_sector_concentration_note(sector_df):
    if sector_df.empty:
        return "No sector data available."

    top_sector = sector_df.iloc[0]

    if top_sector["Weight %"] >= 50:
        return f'Your portfolio is heavily concentrated in {top_sector["Sector"]} at {top_sector["Weight %"]:.2f}%.'

    if top_sector["Weight %"] >= 35:
        return f'Your largest sector is {top_sector["Sector"]} at {top_sector["Weight %"]:.2f}%, so it is worth watching concentration risk.'

    return f'Your largest sector is {top_sector["Sector"]} at {top_sector["Weight %"]:.2f}%.'


def create_dividend_table_html(portfolio_df):
    if portfolio_df.empty or "Dividend Yield %" not in portfolio_df.columns:
        return "<p>No dividend data available.</p>"

    dividend_df = portfolio_df.copy()
    dividend_df["Estimated Annual Dividend"] = pd.to_numeric(dividend_df["Estimated Annual Dividend"], errors="coerce").fillna(0)
    dividend_df = dividend_df.sort_values("Estimated Annual Dividend", ascending=False)

    rows = ""

    for _, row in dividend_df.iterrows():
        rows += f"""
        <tr>
            <td><strong>{escape(str(row["Ticker"]))}</strong></td>
            <td>{escape(str(row["Company"]))}</td>
            <td>{format_percent(row["Dividend Yield %"])}</td>
            <td>{format_money(row["Estimated Annual Dividend"])}</td>
        </tr>
        """

    total_estimated_dividend = dividend_df["Estimated Annual Dividend"].sum()

    return f"""
    <div class="dividend-summary">
        Estimated annual dividend income: <strong>{format_money(total_estimated_dividend)}</strong>
    </div>

    <table class="benchmark-table">
        <thead>
            <tr>
                <th>Ticker</th>
                <th>Company</th>
                <th>Dividend Yield</th>
                <th>Estimated Annual Dividend</th>
            </tr>
        </thead>
        <tbody>
            {rows}
        </tbody>
    </table>
    """


def create_earnings_table_html(portfolio_df, watchlist_df):
    combined_rows = []

    for _, row in portfolio_df.iterrows():
        combined_rows.append({
            "Category": "Portfolio",
            "Ticker": row["Ticker"],
            "Company": row["Company"],
            "Next Earnings Date": row.get("Next Earnings Date", "N/A"),
        })

    if not watchlist_df.empty:
        for _, row in watchlist_df.iterrows():
            combined_rows.append({
                "Category": "Watchlist",
                "Ticker": row["Ticker"],
                "Company": row["Company"],
                "Next Earnings Date": row.get("Next Earnings Date", "N/A"),
            })

    if not combined_rows:
        return "<p>No earnings data available.</p>"

    rows = ""

    for item in combined_rows:
        rows += f"""
        <tr>
            <td>{escape(str(item["Category"]))}</td>
            <td><strong>{escape(str(item["Ticker"]))}</strong></td>
            <td>{escape(str(item["Company"]))}</td>
            <td>{escape(str(item["Next Earnings Date"]))}</td>
        </tr>
        """

    return f"""
    <table class="benchmark-table">
        <thead>
            <tr>
                <th>Category</th>
                <th>Ticker</th>
                <th>Company</th>
                <th>Next Earnings Date</th>
            </tr>
        </thead>
        <tbody>
            {rows}
        </tbody>
    </table>
    """

# ============================================================
# NEWS FUNCTIONS
# ============================================================

def get_nested_value(dictionary, keys, default=None):
    current = dictionary

    for key in keys:
        if not isinstance(current, dict):
            return default

        current = current.get(key)

        if current is None:
            return default

    return current


def extract_news_article(article, ticker):
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

    return {
        "Ticker": ticker,
        "Title": title if title else "No title available",
        "Publisher": publisher if publisher else "Unknown source",
        "Date": date_text,
        "Link": link,
    }


def get_stock_news(tickers, max_articles_per_ticker=3):
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
# BENCHMARK FUNCTIONS
# ============================================================

def get_price_history(ticker, period="6mo"):
    try:
        stock = yf.Ticker(ticker)
        history = stock.history(period=period, interval="1d")

        if history.empty:
            return pd.Series(dtype=float)

        return history["Close"].dropna()
    except Exception as error:
        print(f"Could not get price history for {ticker}: {error}")
        return pd.Series(dtype=float)


def build_portfolio_value_history(portfolio_input):
    portfolio_series = None

    for _, row in portfolio_input.iterrows():
        ticker = row["Ticker"]
        shares = float(row["Shares"])

        prices = get_price_history(ticker)

        if prices.empty:
            continue

        value_series = prices * shares

        if portfolio_series is None:
            portfolio_series = value_series
        else:
            portfolio_series = portfolio_series.add(value_series, fill_value=0)

    if portfolio_series is None or portfolio_series.empty:
        return pd.Series(dtype=float)

    return portfolio_series.dropna()


def calculate_return_from_series(series, days):
    if series is None or series.empty or len(series) <= 1:
        return None

    current = series.iloc[-1]

    if days == "full":
        past = series.iloc[0]
    else:
        if len(series) <= days:
            past = series.iloc[0]
        else:
            past = series.iloc[-days]

    if past == 0:
        return None

    return safe_float(((current - past) / past) * 100)


def get_benchmark_summary(portfolio_input):
    portfolio_series = build_portfolio_value_history(portfolio_input)
    spy_series = get_price_history("SPY")
    qqq_series = get_price_history("QQQ")

    rows = []

    benchmark_items = [
        ("Portfolio", portfolio_series),
        ("SPY", spy_series),
        ("QQQ", qqq_series),
    ]

    for name, series in benchmark_items:
        rows.append({
            "Asset": name,
            "Daily %": calculate_return_from_series(series, 2),
            "1M %": calculate_return_from_series(series, 21),
            "3M %": calculate_return_from_series(series, 63),
            "6M %": calculate_return_from_series(series, "full"),
        })

    df = pd.DataFrame(rows)

    for column in ["Daily %", "1M %", "3M %", "6M %"]:
        df[column] = df[column].apply(lambda value: round(value, 2) if value is not None else None)

    return df, portfolio_series, spy_series, qqq_series


def get_benchmark_verdict(benchmark_df):
    try:
        portfolio_daily = benchmark_df.loc[benchmark_df["Asset"] == "Portfolio", "Daily %"].iloc[0]
        spy_daily = benchmark_df.loc[benchmark_df["Asset"] == "SPY", "Daily %"].iloc[0]
        qqq_daily = benchmark_df.loc[benchmark_df["Asset"] == "QQQ", "Daily %"].iloc[0]

        if pd.isna(portfolio_daily) or pd.isna(spy_daily) or pd.isna(qqq_daily):
            return "Not enough benchmark data yet."

        beat_spy = portfolio_daily > spy_daily
        beat_qqq = portfolio_daily > qqq_daily

        if beat_spy and beat_qqq:
            return "Your portfolio outperformed both SPY and QQQ today."

        if beat_spy and not beat_qqq:
            return "Your portfolio beat SPY today but lagged QQQ."

        if not beat_spy and beat_qqq:
            return "Your portfolio beat QQQ today but lagged SPY."

        return "Your portfolio lagged both SPY and QQQ today."
    except Exception:
        return "Not enough benchmark data yet."


def create_benchmark_table_html(benchmark_df):
    rows = ""

    for _, row in benchmark_df.iterrows():
        rows += f"""
        <tr>
            <td><strong>{escape(str(row["Asset"]))}</strong></td>
            <td class="{get_positive_negative_class(row["Daily %"])}">{get_sign(row["Daily %"])}{format_percent(row["Daily %"])}</td>
            <td class="{get_positive_negative_class(row["1M %"])}">{get_sign(row["1M %"])}{format_percent(row["1M %"])}</td>
            <td class="{get_positive_negative_class(row["3M %"])}">{get_sign(row["3M %"])}{format_percent(row["3M %"])}</td>
            <td class="{get_positive_negative_class(row["6M %"])}">{get_sign(row["6M %"])}{format_percent(row["6M %"])}</td>
        </tr>
        """

    return f"""
    <table class="benchmark-table">
        <thead>
            <tr>
                <th>Asset</th>
                <th>Daily</th>
                <th>1M</th>
                <th>3M</th>
                <th>6M</th>
            </tr>
        </thead>
        <tbody>
            {rows}
        </tbody>
    </table>
    """


def normalize_series(series):
    if series is None or series.empty:
        return pd.Series(dtype=float)

    first_value = series.iloc[0]

    if first_value == 0:
        return pd.Series(dtype=float)

    return (series / first_value) * 100


def create_benchmark_chart(portfolio_series, spy_series, qqq_series):
    fig = go.Figure()

    items = [
        ("Portfolio", portfolio_series),
        ("SPY", spy_series),
        ("QQQ", qqq_series),
    ]

    for name, series in items:
        normalized = normalize_series(series)

        if normalized.empty:
            continue

        fig.add_trace(go.Scatter(
            x=normalized.index,
            y=normalized.values,
            mode="lines",
            name=name
        ))

    fig.update_layout(
        title="Portfolio vs SPY vs QQQ",
        xaxis_title="Date",
        yaxis_title="Starting at 100",
        template="plotly_white",
        legend_title="Benchmark"
    )

    return fig.to_html(full_html=False, include_plotlyjs="cdn")


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
        title="Daily Gain/Loss by Owned Stock",
        xaxis_title="Stock",
        yaxis_title="Gain/Loss",
        template="plotly_white"
    )

    return fig.to_html(full_html=False, include_plotlyjs="cdn")


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

    return fig.to_html(full_html=False, include_plotlyjs="cdn")


def create_allocation_chart(df):
    fig = px.pie(
        df,
        names="Ticker",
        values="Current Value",
        title="Portfolio Allocation"
    )

    fig.update_traces(textposition="inside", textinfo="percent+label")
    fig.update_layout(template="plotly_white")

    return fig.to_html(full_html=False, include_plotlyjs="cdn")


def create_watchlist_movers_chart(watchlist_df):
    if watchlist_df.empty:
        return ""

    sorted_df = watchlist_df.sort_values("Daily Change %", ascending=False).copy()

    if sorted_df.empty:
        return ""

    colors = ["green" if value >= 0 else "red" for value in sorted_df["Daily Change %"]]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=sorted_df["Ticker"],
        y=sorted_df["Daily Change %"],
        text=[f"{value:.2f}%" for value in sorted_df["Daily Change %"]],
        textposition="outside",
        marker_color=colors
    ))

    fig.update_layout(
        title="Watchlist Daily Movers",
        xaxis_title="Ticker",
        yaxis_title="Daily Change %",
        template="plotly_white"
    )

    return fig.to_html(full_html=False, include_plotlyjs="cdn")


def create_watchlist_rsi_chart(watchlist_df):
    if watchlist_df.empty or "RSI" not in watchlist_df.columns:
        return ""

    clean_df = watchlist_df.dropna(subset=["RSI"]).copy()

    if clean_df.empty:
        return ""

    colors = []

    for value in clean_df["RSI"]:
        if value >= 70:
            colors.append("red")
        elif value <= 30:
            colors.append("green")
        else:
            colors.append("gray")

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=clean_df["Ticker"],
        y=clean_df["RSI"],
        text=[f"{value:.2f}" for value in clean_df["RSI"]],
        textposition="outside",
        marker_color=colors
    ))

    fig.add_hline(y=70, line_dash="dash", annotation_text="Overbought")
    fig.add_hline(y=30, line_dash="dash", annotation_text="Oversold")

    fig.update_layout(
        title="Watchlist RSI",
        xaxis_title="Ticker",
        yaxis_title="RSI",
        template="plotly_white"
    )

    return fig.to_html(full_html=False, include_plotlyjs="cdn")


def create_moving_average_chart(tickers):
    fig = go.Figure()

    for ticker in tickers:
        data = get_stock_data(ticker)

        if data is None:
            continue

        history = data["history"].copy()

        if history.empty:
            continue

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

    return fig.to_html(full_html=False, include_plotlyjs="cdn")


def create_volatility_chart(df):
    fig = px.bar(
        df,
        x="Ticker",
        y="Annualized Volatility %",
        title="Owned Stock Annualized Volatility",
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

    return fig.to_html(full_html=False, include_plotlyjs="cdn")


# ============================================================
# AI SUMMARY
# ============================================================

def generate_ai_summary(portfolio_df, watchlist_df, portfolio_news, watchlist_news, benchmark_df, benchmark_verdict, sector_note):
    total_value = portfolio_df["Current Value"].sum()
    previous_value = portfolio_df["Previous Value"].sum()
    total_daily_gain_loss = portfolio_df["Daily Gain/Loss"].sum()
    total_daily_percent = (total_daily_gain_loss / previous_value) * 100 if previous_value != 0 else 0

    total_cost_basis = portfolio_df["Cost Basis"].sum()
    total_unrealized_gain_loss = portfolio_df["Total Gain/Loss"].sum()
    total_unrealized_percent = (total_unrealized_gain_loss / total_cost_basis) * 100 if total_cost_basis > 0 else 0

    best_stock = portfolio_df.loc[portfolio_df["Daily Gain/Loss"].idxmax()]
    worst_stock = portfolio_df.loc[portfolio_df["Daily Gain/Loss"].idxmin()]
    largest_position = portfolio_df.loc[portfolio_df["Portfolio Weight %"].idxmax()]

    if watchlist_df.empty:
        watchlist_text = "No watchlist stocks found."
    else:
        watchlist_text = watchlist_df.to_string(index=False)

    portfolio_news_text = news_items_to_text(portfolio_news, max_items=8)
    watchlist_news_text = news_items_to_text(watchlist_news, max_items=8)
    benchmark_text = benchmark_df.to_string(index=False)

    prompt = f"""
You are an AI financial dashboard assistant.

Formatting rules:
Do not use markdown.
Do not use asterisks.
Do not use hashtags.
Use plain sentences only.
Every bullet must be a complete sentence.
Do not split one sentence across multiple bullets.
Do not create short continuation bullets like "from previous close" or "average cost."
Keep the entire summary short, professional, and easy to read.
Do not give official financial advice.

Portfolio data:
{portfolio_df.to_string(index=False)}

Watchlist data:
{watchlist_text}

Benchmark data:
{benchmark_text}

Benchmark result:
{benchmark_verdict}

Sector concentration note:
{sector_note}

Recent portfolio news:
{portfolio_news_text}

Recent watchlist news:
{watchlist_news_text}

Write this exact structure:

Portfolio Summary:
- Explain today's total portfolio movement.
- Mention total portfolio value.
- Mention daily gain or loss.

Best Performer:
- Explain which owned stock helped the most today.

Worst Performer:
- Explain which owned stock hurt the most today.

Total Gain or Loss:
- Explain total gain or loss compared to average cost.

Portfolio vs Market:
- Explain whether the portfolio beat or lagged SPY and QQQ today.
- Keep it simple.

Sector Allocation:
- Mention the sector concentration note.

Risk and Trend Notes:
- Mention RSI, moving averages, volatility, and allocation.
- Mention if the portfolio depends heavily on one stock.

Watchlist Summary:
- Explain the strongest watchlist movers.
- Mention which watchlist stocks look worth researching based on trend, RSI, and daily movement.

Market and Stock News:
- Summarize important portfolio and watchlist news.
- Explain which news may matter.
- If the news is not clearly connected to price movement, say that clearly.

Beginner Takeaway:
- Give one simple takeaway.
"""

    try:
        result = subprocess.run(
            ["ollama", "run", "llama3.2"],
            input=prompt,
            text=True,
            capture_output=True,
            timeout=140
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
The best owned stock today is {best_stock["Ticker"]}, with a daily impact of {format_money(best_stock["Daily Gain/Loss"])}.

Worst Performer:
The weakest owned stock today is {worst_stock["Ticker"]}, with a daily impact of {format_money(worst_stock["Daily Gain/Loss"])}.

Total Gain or Loss:
Your total gain or loss compared to average cost is {get_sign(total_unrealized_gain_loss)}{format_money(total_unrealized_gain_loss)}, which is {get_sign(total_unrealized_percent)}{format_percent(total_unrealized_percent)}.

Portfolio vs Market:
{benchmark_verdict}

Sector Allocation:
{sector_note}

Risk and Trend Notes:
Your largest position is {largest_position["Ticker"]}, which is {format_percent(largest_position["Portfolio Weight %"])} of your portfolio.
Watch allocation, moving averages, RSI, volatility, and whether too much of the portfolio depends on one stock.

Watchlist Summary:
Use the watchlist table to compare RSI, trend signals, volatility, daily movement, and research signals.

Market and Stock News:
The dashboard found {len(portfolio_news)} portfolio news items and {len(watchlist_news)} watchlist news items.
Read the news cards below to see what may affect your stocks.

Beginner Takeaway:
Separate stocks you own from stocks you are researching, and compare your portfolio against benchmarks like SPY and QQQ.
"""

    return clean_ai_text(backup)


# ============================================================
# HTML REPORT
# ============================================================

def create_moving_ticker(portfolio_df, watchlist_df):
    ticker_items = ""
    combined = []

    for _, row in portfolio_df.iterrows():
        combined.append((row, "Owned"))

    for _, row in watchlist_df.iterrows():
        combined.append((row, "Watchlist"))

    for row, label in combined:
        change_class = get_positive_negative_class(row["Daily Change %"])
        sign = get_sign(row["Daily Change %"])

        ticker_items += f"""
        <div class="ticker-item">
            <div class="ticker-label">{label}</div>
            <div class="ticker-symbol">{escape(str(row["Ticker"]))}</div>
            <div class="ticker-company">{escape(str(row["Company"]))}</div>
            <div class="ticker-price">{format_money(row["Current Price"])}</div>
            <div class="{change_class}">{sign}{format_percent(row["Daily Change %"])}</div>
        </div>
        """

    return ticker_items + ticker_items


def create_portfolio_table_html(df):
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


def create_watchlist_table_html(df):
    if df.empty:
        return "<p>No watchlist stocks found.</p>"

    rows = ""

    for _, row in df.iterrows():
        daily_class = get_positive_negative_class(row["Daily Change %"])
        five_day_class = get_positive_negative_class(row["5D Return %"])
        one_month_class = get_positive_negative_class(row["1M Return %"])
        three_month_class = get_positive_negative_class(row["3M Return %"])

        rows += f"""
        <tr>
            <td><strong>{escape(str(row["Ticker"]))}</strong></td>
            <td>{escape(str(row["Company"]))}</td>
            <td>{format_money(row["Current Price"])}</td>
            <td class="{daily_class}">{get_sign(row["Daily Change %"])}{format_percent(row["Daily Change %"])}</td>
            <td class="{five_day_class}">{get_sign(row["5D Return %"])}{format_percent(row["5D Return %"])}</td>
            <td class="{one_month_class}">{get_sign(row["1M Return %"])}{format_percent(row["1M Return %"])}</td>
            <td class="{three_month_class}">{get_sign(row["3M Return %"])}{format_percent(row["3M Return %"])}</td>
            <td>{row["RSI"] if pd.notna(row["RSI"]) else "N/A"}</td>
            <td>{escape(str(row["RSI Signal"]))}</td>
            <td>{escape(str(row["Trend Signal"]))}</td>
            <td>{format_percent(row["Annualized Volatility %"])}</td>
            <td>{format_money(row["52W High"])}</td>
            <td>{format_money(row["52W Low"])}</td>
            <td>{format_percent(row["Distance From 52W High %"])}</td>
            <td>{format_large_number(row["Market Cap"])}</td>
            <td><strong>{escape(str(row["Research Signal"]))}</strong></td>
        </tr>
        """

    return f"""
    <table class="portfolio-table">
        <thead>
            <tr>
                <th>Ticker</th>
                <th>Company</th>
                <th>Price</th>
                <th>Daily %</th>
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
                <th>Market Cap</th>
                <th>Research Signal</th>
            </tr>
        </thead>
        <tbody>
            {rows}
        </tbody>
    </table>
    """


def create_html_report(portfolio_input, portfolio_df, watchlist_df, ai_summary, portfolio_news, watchlist_news, benchmark_df, benchmark_verdict, benchmark_chart, sector_df, sector_note):
    REPORTS_FOLDER.mkdir(exist_ok=True)

    total_value = portfolio_df["Current Value"].sum()
    previous_value = portfolio_df["Previous Value"].sum()
    total_daily_gain_loss = portfolio_df["Daily Gain/Loss"].sum()
    total_daily_percent = (total_daily_gain_loss / previous_value) * 100 if previous_value != 0 else 0

    total_cost_basis = portfolio_df["Cost Basis"].sum()
    total_gain_loss = portfolio_df["Total Gain/Loss"].sum()
    total_gain_loss_percent = (total_gain_loss / total_cost_basis) * 100 if total_cost_basis > 0 else 0

    best_stock = portfolio_df.loc[portfolio_df["Daily Gain/Loss"].idxmax()]
    worst_stock = portfolio_df.loc[portfolio_df["Daily Gain/Loss"].idxmin()]

    portfolio_tickers = portfolio_df["Ticker"].tolist()
    watchlist_tickers = watchlist_df["Ticker"].tolist() if not watchlist_df.empty else []
    all_tickers = list(dict.fromkeys(portfolio_tickers + watchlist_tickers))

    dashboard_alerts = build_dashboard_alerts(portfolio_df, watchlist_df)
    alert_count = len(dashboard_alerts)

    ticker_html = create_moving_ticker(portfolio_df, watchlist_df)
    portfolio_table_html = create_portfolio_table_html(portfolio_df)
    watchlist_table_html = create_watchlist_table_html(watchlist_df)
    ai_summary_html = format_ai_summary_as_html(ai_summary)
    alerts_html = create_alert_cards_html(dashboard_alerts)
    benchmark_table_html = create_benchmark_table_html(benchmark_df)
    sector_cards_html = create_sector_cards_html(sector_df)
    sector_chart = create_sector_pie_chart(sector_df)
    sector_table_html = create_sector_table_html(sector_df)
    dividend_table_html = create_dividend_table_html(portfolio_df)
    earnings_table_html = create_earnings_table_html(portfolio_df, watchlist_df)

    portfolio_news_html = create_news_html(portfolio_news)
    watchlist_news_html = create_news_html(watchlist_news)

    portfolio_value_chart = create_portfolio_value_chart(portfolio_df)
    daily_gain_loss_chart = create_daily_gain_loss_chart(portfolio_df)
    total_gain_loss_chart = create_total_gain_loss_chart(portfolio_df)
    allocation_chart = create_allocation_chart(portfolio_df)

    watchlist_movers_chart = create_watchlist_movers_chart(watchlist_df)
    watchlist_rsi_chart = create_watchlist_rsi_chart(watchlist_df)

    watchlist_movers_section = wrap_section(watchlist_movers_chart)
    watchlist_rsi_section = wrap_section(watchlist_rsi_chart)

    moving_average_chart = create_moving_average_chart(all_tickers)
    volatility_chart = create_volatility_chart(portfolio_df)

    portfolio_daily = benchmark_df.loc[benchmark_df["Asset"] == "Portfolio", "Daily %"].iloc[0]
    spy_daily = benchmark_df.loc[benchmark_df["Asset"] == "SPY", "Daily %"].iloc[0]
    qqq_daily = benchmark_df.loc[benchmark_df["Asset"] == "QQQ", "Daily %"].iloc[0]

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
            max-width: 1350px;
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
            animation: tickerMove 32s linear infinite;
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
            min-width: 185px;
            background: #1f2937;
            color: white;
            padding: 14px;
            border-radius: 14px;
            text-align: center;
            flex-shrink: 0;
        }}

        .ticker-label {{
            display: inline-block;
            font-size: 11px;
            background: #374151;
            color: #e5e7eb;
            padding: 3px 8px;
            border-radius: 999px;
            margin-bottom: 6px;
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

        .snapshot-cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
            gap: 18px;
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

        .section-intro {{
            color: #666;
            margin-top: -5px;
            margin-bottom: 18px;
            line-height: 1.5;
        }}

                .ai-summary {{
            line-height: 1.7;
            background: #f9fafb;
            padding: 18px;
            border-radius: 12px;
            border-left: 5px solid #111827;
            max-width: 100%;
            box-sizing: border-box;
            overflow-wrap: break-word;
            word-wrap: break-word;
            word-break: normal;
            white-space: normal;
        }}

        .ai-summary h3 {{
            margin-bottom: 8px;
            margin-top: 18px;
            color: #111827;
            overflow-wrap: break-word;
            word-wrap: break-word;
            white-space: normal;
        }}

        .ai-summary h3:first-child {{
            margin-top: 0;
        }}

        .ai-summary ul {{
            margin-top: 5px;
            margin-bottom: 12px;
            padding-left: 24px;
            overflow-wrap: break-word;
            word-wrap: break-word;
            white-space: normal;
        }}

        .ai-summary li {{
            margin-bottom: 8px;
            overflow-wrap: break-word;
            word-wrap: break-word;
            white-space: normal;
        }}


        .portfolio-table,
        .benchmark-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }}

        .portfolio-table th,
        .portfolio-table td,
        .benchmark-table th,
        .benchmark-table td {{
            border: 1px solid #ddd;
            padding: 9px;
            text-align: center;
            white-space: nowrap;
        }}

        .portfolio-table th,
        .benchmark-table th {{
            background: #111827;
            color: white;
        }}

        .portfolio-table tr:nth-child(even),
        .benchmark-table tr:nth-child(even) {{
            background: #f9fafb;
        }}

        .benchmark-grid {{
            display: grid;
            grid-template-columns: 1.2fr 1fr;
            gap: 20px;
            align-items: start;
        }}

        .benchmark-result {{
            background: #f9fafb;
            border-radius: 14px;
            padding: 18px;
            border-left: 5px solid #111827;
            margin-bottom: 18px;
            font-weight: bold;
            line-height: 1.5;
        }}

        .mini-metric-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
            gap: 12px;
            margin-bottom: 18px;
        }}

        .mini-metric {{
            background: #f9fafb;
            border-radius: 14px;
            padding: 14px;
            text-align: center;
            border: 1px solid #e5e7eb;
        }}

        .mini-label {{
            color: #666;
            font-size: 13px;
            margin-bottom: 6px;
        }}

        .mini-value {{
            font-size: 20px;
            font-weight: bold;
        }}

        .alerts-container {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 20px;
        }}

        .alert-group h3 {{
            margin-top: 0;
            color: #111827;
        }}

        .alert-grid {{
            display: grid;
            gap: 12px;
        }}

        .alert-card {{
            border-radius: 14px;
            padding: 16px;
            border-left: 6px solid #111827;
            background: #f9fafb;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        }}

        .alert-high {{
            border-left-color: red;
            background: #fff5f5;
        }}

        .alert-medium {{
            border-left-color: orange;
            background: #fffaf0;
        }}

        .alert-low {{
            border-left-color: #2563eb;
            background: #eff6ff;
        }}

        .alert-top {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 10px;
            margin-bottom: 8px;
        }}

        .alert-ticker {{
            font-size: 18px;
            font-weight: bold;
            color: #111827;
        }}

        .alert-type {{
            font-size: 12px;
            background: #111827;
            color: white;
            padding: 5px 8px;
            border-radius: 999px;
            white-space: nowrap;
        }}

        .alert-message {{
            color: #333;
            line-height: 1.4;
        }}

        .alert-empty {{
            background: #f9fafb;
            color: #666;
            padding: 16px;
            border-radius: 14px;
            border: 1px solid #e5e7eb;
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

        .sector-card-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
            gap: 14px;
            margin-bottom: 20px;
        }}

        .sector-card {{
            background: #f9fafb;
            border: 1px solid #e5e7eb;
            border-radius: 14px;
            padding: 16px;
            text-align: center;
        }}

        .sector-name {{
            color: #555;
            font-size: 14px;
            margin-bottom: 8px;
        }}

        .sector-weight {{
            font-size: 24px;
            font-weight: bold;
            color: #111827;
        }}

        .sector-value {{
            color: #777;
            margin-top: 6px;
            font-size: 13px;
        }}

        .dividend-summary {{
            background: #f9fafb;
            border-left: 5px solid #111827;
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 18px;
            line-height: 1.5;
        }}

        .action-buttons {{
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
        }}

        .action-button {{
            border: none;
            background: #111827;
            color: white;
            padding: 12px 16px;
            border-radius: 12px;
            cursor: pointer;
            font-weight: bold;
        }}

        .action-button:hover {{
            background: #374151;
        }}

        @media (max-width: 900px) {{
            .benchmark-grid {{
                grid-template-columns: 1fr;
            }}
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

        <div class="snapshot-cards">
            <div class="card">
                <h2>Total Portfolio Value</h2>
                <div class="value">{format_money(total_value)}</div>
                <div class="small-note">Current value of your owned holdings</div>
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
                <h2>Alerts Triggered</h2>
                <div class="value">{alert_count}</div>
                <div class="small-note">portfolio and watchlist signals</div>
            </div>
        </div>

        <div class="section">
            <h2>AI Summary</h2>
            <div class="ai-summary">
                {ai_summary_html}
            </div>
        </div>

        <div class="section">
            <h2>Portfolio vs Market</h2>
            <p class="section-intro">Compares your portfolio against SPY and QQQ so you can quickly see if you are beating or lagging the market.</p>

            <div class="benchmark-result">
                {escape(benchmark_verdict)}
            </div>

            <div class="mini-metric-grid">
                <div class="mini-metric">
                    <div class="mini-label">Portfolio Today</div>
                    <div class="mini-value {get_positive_negative_class(portfolio_daily)}">{get_sign(portfolio_daily)}{format_percent(portfolio_daily)}</div>
                </div>

                <div class="mini-metric">
                    <div class="mini-label">SPY Today</div>
                    <div class="mini-value {get_positive_negative_class(spy_daily)}">{get_sign(spy_daily)}{format_percent(spy_daily)}</div>
                </div>

                <div class="mini-metric">
                    <div class="mini-label">QQQ Today</div>
                    <div class="mini-value {get_positive_negative_class(qqq_daily)}">{get_sign(qqq_daily)}{format_percent(qqq_daily)}</div>
                </div>
            </div>

            <div class="benchmark-grid">
                <div>
                    {benchmark_chart}
                </div>

                <div>
                    {benchmark_table_html}
                </div>
            </div>
        </div>

        <div class="section">
            <h2>Sector Allocation</h2>
            <p class="section-intro">{escape(sector_note)}</p>
            {sector_cards_html}
            <div class="benchmark-grid">
                <div>
                    {sector_chart}
                </div>
                <div>
                    {sector_table_html}
                </div>
            </div>
        </div>

        <div class="section">
            <h2>Dividends</h2>
            <p class="section-intro">Estimates annual dividend income from your current holdings when dividend yield data is available.</p>
            {dividend_table_html}
        </div>

        <div class="section">
            <h2>Earnings Dates</h2>
            <p class="section-intro">Tracks upcoming earnings dates for portfolio and watchlist stocks when yfinance provides the data.</p>
            {earnings_table_html}
        </div>

        <div class="section">
            <h2>Report Actions</h2>
            <p class="section-intro">Use this when you want to save or share the report.</p>
            <div class="action-buttons">
                <button class="action-button" onclick="window.print()">Print or Save as PDF</button>
                <button class="action-button" onclick="window.location.href='mailto:?subject=AI Financial Dashboard Report&body=Open the latest dashboard report saved on this computer.'">Open Email Draft</button>
            </div>
        </div>

        <div class="section">
            <h2>Alerts</h2>
            {alerts_html}
        </div>

        <div class="section">
            <h2>Watchlist Metrics Table</h2>
            {watchlist_table_html}
        </div>

        {watchlist_movers_section}

        {watchlist_rsi_section}

        <div class="section">
            <h2>Watchlist News</h2>
            {watchlist_news_html}
        </div>

        <div class="section">
            <h2>Portfolio Metrics Table</h2>
            {portfolio_table_html}
        </div>

        <div class="section">
            <h2>Portfolio News</h2>
            {portfolio_news_html}
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
            {moving_average_chart}
        </div>

        <div class="section">
            {volatility_chart}
        </div>

        <p class="footer">
            Portfolio stocks are stocks you own. Watchlist stocks are stocks you are researching. SPY and QQQ are used as simple market benchmarks. Data and news are latest available from yfinance and are not professional tick-by-tick trading data. This is not financial advice.
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

    watchlist_input = load_watchlist()
    print("Watchlist input loaded.")

    portfolio_df = build_portfolio_dataframe(portfolio_input)

    if portfolio_df.empty:
        print("No stock data found. Check your portfolio tickers or internet connection.")
        return

    print("Portfolio data loaded.")
    print(portfolio_df)

    watchlist_df = build_watchlist_dataframe(watchlist_input)

    if watchlist_df.empty:
        print("No watchlist data found. Continuing with portfolio only.")
    else:
        print("Watchlist data loaded.")
        print(watchlist_df)

    print("Building benchmark comparison...")
    benchmark_df, portfolio_series, spy_series, qqq_series = get_benchmark_summary(portfolio_input)
    benchmark_verdict = get_benchmark_verdict(benchmark_df)
    benchmark_chart = create_benchmark_chart(portfolio_series, spy_series, qqq_series)
    print("Benchmark comparison created.")

    print("Building sector allocation...")
    sector_df = build_sector_allocation(portfolio_df)
    sector_note = get_sector_concentration_note(sector_df)
    print("Sector allocation created.")

    portfolio_tickers = portfolio_df["Ticker"].tolist()
    watchlist_tickers = watchlist_df["Ticker"].tolist() if not watchlist_df.empty else []

    print("Gathering recent portfolio news...")
    portfolio_news = get_stock_news(portfolio_tickers)
    print(f"Found {len(portfolio_news)} portfolio news items.")

    print("Gathering recent watchlist news...")
    watchlist_news = get_stock_news(watchlist_tickers)
    print(f"Found {len(watchlist_news)} watchlist news items.")

    ai_summary = generate_ai_summary(
        portfolio_df,
        watchlist_df,
        portfolio_news,
        watchlist_news,
        benchmark_df,
        benchmark_verdict,
        sector_note
    )
    print("AI summary created.")

    report_path = create_html_report(
        portfolio_input,
        portfolio_df,
        watchlist_df,
        ai_summary,
        portfolio_news,
        watchlist_news,
        benchmark_df,
        benchmark_verdict,
        benchmark_chart,
        sector_df,
        sector_note
    )

    print(f"Report saved to: {report_path}")

    open_report(report_path)

    send_mac_notification(
        "AI Financial Dashboard",
        "Your dashboard with final features is ready."
    )


if __name__ == "__main__":
    main()
