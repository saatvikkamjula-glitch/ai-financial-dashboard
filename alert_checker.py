import math
import platform
import subprocess
from datetime import datetime
from pathlib import Path

import pandas as pd
import yfinance as yf


# ============================================================
# FILE SETTINGS
# ============================================================

PORTFOLIO_FILE = Path("portfolio.csv")
WATCHLIST_FILE = Path("watchlist.csv")
REPORTS_FOLDER = Path("reports")


# ============================================================
# ALERT SETTINGS
# ============================================================

DAILY_MOVE_ALERT_PERCENT = 3
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30
NEAR_52_WEEK_HIGH_PERCENT = -5
FAR_FROM_52_WEEK_HIGH_PERCENT = -25


# ============================================================
# NOTIFICATION
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


# ============================================================
# INPUT LOADING
# ============================================================

def load_tickers_from_portfolio():
    if not PORTFOLIO_FILE.exists():
        return []

    try:
        df = pd.read_csv(PORTFOLIO_FILE)

        if "Ticker" not in df.columns:
            return []

        tickers = (
            df["Ticker"]
            .astype(str)
            .str.upper()
            .str.strip()
            .dropna()
            .tolist()
        )

        return [ticker for ticker in tickers if ticker]

    except Exception:
        return []


def load_tickers_from_watchlist():
    if not WATCHLIST_FILE.exists():
        return []

    try:
        df = pd.read_csv(WATCHLIST_FILE)

        if "Ticker" not in df.columns:
            return []

        tickers = (
            df["Ticker"]
            .astype(str)
            .str.upper()
            .str.strip()
            .dropna()
            .tolist()
        )

        return [ticker for ticker in tickers if ticker]

    except Exception:
        return []


def load_all_tracked_tickers():
    portfolio_tickers = load_tickers_from_portfolio()
    watchlist_tickers = load_tickers_from_watchlist()

    all_tickers = []

    for ticker in portfolio_tickers:
        all_tickers.append({
            "Ticker": ticker,
            "Category": "Portfolio"
        })

    for ticker in watchlist_tickers:
        all_tickers.append({
            "Ticker": ticker,
            "Category": "Watchlist"
        })

    seen = set()
    unique_tickers = []

    for item in all_tickers:
        ticker = item["Ticker"]

        if ticker not in seen:
            unique_tickers.append(item)
            seen.add(ticker)

    return unique_tickers


# ============================================================
# STOCK DATA
# ============================================================

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


def get_fast_info_value(stock, key):
    try:
        return safe_float(stock.fast_info.get(key))
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


def get_stock_snapshot(ticker):
    try:
        stock = yf.Ticker(ticker)
        history = stock.history(period="6mo", interval="1d")

        if history.empty or len(history) < 2:
            return None

        history = history.dropna()

        latest_close = safe_float(history["Close"].iloc[-1])
        previous_close_history = safe_float(history["Close"].iloc[-2])

        last_price = get_fast_info_value(stock, "last_price")
        previous_close_fast = get_fast_info_value(stock, "previous_close")
        year_high = get_fast_info_value(stock, "year_high")
        year_low = get_fast_info_value(stock, "year_low")

        current_price = last_price if last_price is not None else latest_close
        previous_close = previous_close_fast if previous_close_fast is not None else previous_close_history

        if current_price is None or previous_close is None or previous_close == 0:
            return None

        daily_change = current_price - previous_close
        daily_change_percent = (daily_change / previous_close) * 100

        rsi = calculate_rsi(history["Close"])

        distance_from_52w_high = None

        if year_high is not None and year_high != 0:
            distance_from_52w_high = ((current_price - year_high) / year_high) * 100

        return {
            "Ticker": ticker,
            "Current Price": round(current_price, 2),
            "Previous Close": round(previous_close, 2),
            "Daily Change": round(daily_change, 2),
            "Daily Change %": round(daily_change_percent, 2),
            "RSI": round(rsi, 2) if rsi is not None else None,
            "52W High": round(year_high, 2) if year_high is not None else None,
            "52W Low": round(year_low, 2) if year_low is not None else None,
            "Distance From 52W High %": round(distance_from_52w_high, 2) if distance_from_52w_high is not None else None,
        }

    except Exception as error:
        print(f"Could not get data for {ticker}: {error}")
        return None


# ============================================================
# ALERT LOGIC
# ============================================================

def check_alert_conditions(category, snapshot):
    alerts = []

    ticker = snapshot["Ticker"]
    current_price = snapshot["Current Price"]
    daily_change_percent = snapshot["Daily Change %"]
    rsi = snapshot["RSI"]
    distance_from_high = snapshot["Distance From 52W High %"]

    if abs(daily_change_percent) >= DAILY_MOVE_ALERT_PERCENT:
        direction = "up" if daily_change_percent >= 0 else "down"

        alerts.append({
            "Ticker": ticker,
            "Category": category,
            "Alert Type": "Large Daily Move",
            "Message": f"{ticker} is {direction} {daily_change_percent:.2f}% today.",
        })

    if rsi is not None and rsi >= RSI_OVERBOUGHT:
        alerts.append({
            "Ticker": ticker,
            "Category": category,
            "Alert Type": "RSI Overbought",
            "Message": f"{ticker} has RSI of {rsi:.2f}, which is above {RSI_OVERBOUGHT}.",
        })

    if rsi is not None and rsi <= RSI_OVERSOLD:
        alerts.append({
            "Ticker": ticker,
            "Category": category,
            "Alert Type": "RSI Oversold",
            "Message": f"{ticker} has RSI of {rsi:.2f}, which is below {RSI_OVERSOLD}.",
        })

    if distance_from_high is not None and distance_from_high >= NEAR_52_WEEK_HIGH_PERCENT:
        alerts.append({
            "Ticker": ticker,
            "Category": category,
            "Alert Type": "Near 52-Week High",
            "Message": f"{ticker} is close to its 52-week high. Current price is ${current_price:.2f}.",
        })

    if distance_from_high is not None and distance_from_high <= FAR_FROM_52_WEEK_HIGH_PERCENT:
        alerts.append({
            "Ticker": ticker,
            "Category": category,
            "Alert Type": "Far From 52-Week High",
            "Message": f"{ticker} is {distance_from_high:.2f}% below its 52-week high.",
        })

    return alerts


# ============================================================
# MAIN ALERT CHECKER
# ============================================================

def check_alerts():
    REPORTS_FOLDER.mkdir(exist_ok=True)

    tracked_tickers = load_all_tracked_tickers()

    if not tracked_tickers:
        print("No portfolio or watchlist tickers found.")
        return pd.DataFrame()

    print("\nChecking alerts for portfolio and watchlist stocks...\n")

    all_results = []
    triggered_alerts = []

    for item in tracked_tickers:
        ticker = item["Ticker"]
        category = item["Category"]

        snapshot = get_stock_snapshot(ticker)

        if snapshot is None:
            all_results.append({
                "Ticker": ticker,
                "Category": category,
                "Current Price": None,
                "Daily Change %": None,
                "RSI": None,
                "Distance From 52W High %": None,
                "Triggered": False,
                "Alert Type": "Data Error",
                "Message": "Could not get stock data.",
            })

            print(f"{ticker}: Could not get stock data.")
            continue

        alerts = check_alert_conditions(category, snapshot)

        if alerts:
            for alert in alerts:
                triggered_alerts.append(alert)

                all_results.append({
                    "Ticker": ticker,
                    "Category": category,
                    "Current Price": snapshot["Current Price"],
                    "Daily Change %": snapshot["Daily Change %"],
                    "RSI": snapshot["RSI"],
                    "Distance From 52W High %": snapshot["Distance From 52W High %"],
                    "Triggered": True,
                    "Alert Type": alert["Alert Type"],
                    "Message": alert["Message"],
                })

                print(f"{ticker}: TRIGGERED — {alert['Message']}")
        else:
            all_results.append({
                "Ticker": ticker,
                "Category": category,
                "Current Price": snapshot["Current Price"],
                "Daily Change %": snapshot["Daily Change %"],
                "RSI": snapshot["RSI"],
                "Distance From 52W High %": snapshot["Distance From 52W High %"],
                "Triggered": False,
                "Alert Type": "None",
                "Message": "No alert triggered.",
            })

            print(f"{ticker}: No alert triggered.")

    results_df = pd.DataFrame(all_results)

    report_name = f"alerts_report_{datetime.now().strftime('%Y-%m-%d')}.csv"
    report_path = REPORTS_FOLDER / report_name
    results_df.to_csv(report_path, index=False)

    print("\nAlert check complete.")
    print(f"Triggered alerts: {len(triggered_alerts)}")
    print(f"Alert report saved to: {report_path}")

    if triggered_alerts:
        first_alert = triggered_alerts[0]
        send_mac_notification(
            "Stock Alert Triggered",
            first_alert["Message"]
        )

        if len(triggered_alerts) > 1:
            send_mac_notification(
                "More Stock Alerts",
                f"{len(triggered_alerts)} total alerts were triggered."
            )
    else:
        send_mac_notification(
            "Stock Alerts Checked",
            "No portfolio or watchlist alerts were triggered."
        )

    return results_df


def main():
    check_alerts()


if __name__ == "__main__":
    main()