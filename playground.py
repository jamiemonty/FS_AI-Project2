"""
GPT Prompt: Create a stock trading strategy using Bollinger Bands with compound returns tracking
Features:
- Backtest strategy for 2014–2025
- Uses Bollinger Bands for buy/sell signals
- Sequential trades allowed (same-day rebuys)
- Creates trade spreadsheet + metrics
- Generates charts
- Calculates compound returns per year and over 12 years
"""

# Import libraries for data processing, file handling, and charting
import pandas as pd, numpy as np, os, glob, mplfinance as mpf, matplotlib.pyplot as plt
from datetime import datetime

# --- Strategy Parameters ---
# These control the Bollinger Band calculation and trading rules
period, std_factor = 20, 2  # 20-day moving average with 2 standard deviations
max_hold_days, min_volume = 30, 100000  # Maximum days to hold position and minimum volume filter
deviation_threshold = 0.02  # Price must be at least 2% below lower band to trigger buy
initial_capital = 10000  # Starting capital for backtesting
years_to_test = list(range(2014, 2026))  # Years to backtest (2014-2025)

strategy_description = (
    "We use daily Adj Close prices to generate buy signals when the price falls below the "
    "lower Bollinger Band (20-day, 2σ), provided the deviation is >2% and volume >100k. "
    "Sell when the price crosses the SMA or after 30 days. Capital compounds after each trade."
)

# ============================================================
# FUNCTION: calculate_bands
# PURPOSE: Calculates Bollinger Bands indicators for a stock
# INPUT: DataFrame with 'Close' prices
# OUTPUT: Same DataFrame with added SMA, Upper/Lower bands, and %Below_Lower columns
# ============================================================
def calculate_bands(df):
    df["SMA"] = df["Close"].rolling(period).mean()  # Simple Moving Average
    df["STD"] = df["Close"].rolling(period).std()  # Standard Deviation
    df["Upper"] = df["SMA"] + std_factor * df["STD"]  # Upper Bollinger Band
    df["Lower"] = df["SMA"] - std_factor * df["STD"]  # Lower Bollinger Band
    df["%Below_Lower"] = (df["Lower"] - df["Close"]) / df["Close"]  # How far price is below lower band
    return df

# ============================================================
# FUNCTION: find_signals
# PURPOSE: Scans stock data to find buy/sell signals using Bollinger Band strategy
# BUY SIGNAL: Price drops below lower band by >2%, volume > 100k
# SELL SIGNAL: Price crosses above SMA OR held for 30 days
# OUTPUT: List of trades (buy_date, buy_price, sell_date, sell_price, deviation, days_held)
# ============================================================
def find_signals(df):
    trades, in_position, entry_date, entry_price = [], False, None, None
    for i in range(len(df)):
        today = df.index[i]
        price, vol = df["Close"].iloc[i], df["Volume"].iloc[i]
        sma, lower, below = df["SMA"].iloc[i], df["Lower"].iloc[i], df["%Below_Lower"].iloc[i]
        
        # Look for buy opportunity when not in a position
        if not in_position:
            if price < lower and below > deviation_threshold and vol > min_volume:
                in_position, entry_date, entry_price = True, today, price
        else:
            # Check exit conditions when holding a position
            days_held = (today - entry_date).days
            if price > sma or days_held >= max_hold_days:
                trades.append((entry_date, entry_price, today, price, below, days_held))
                in_position = False
    return trades

# ============================================================
# FUNCTION: plot_chart
# PURPOSE: Creates and saves a candlestick chart with Bollinger Bands and trade signals
# - Shows price candles with volume
# - Overlays SMA and Bollinger Bands
# - Marks buy signals (green lines) and sell signals (red lines)
# ============================================================
def plot_chart(df, signals, ticker, year):
    os.makedirs("plots", exist_ok=True)
    # Set up Bollinger Bands and SMA as additional plot layers
    apds = [mpf.make_addplot(df["Upper"], color='gray', alpha=0.5),
            mpf.make_addplot(df["Lower"], color='gray', alpha=0.5),
            mpf.make_addplot(df["SMA"], color='blue', alpha=0.5)]
    
    # Create vertical lines for buy (green) and sell (red) dates
    vdates, vcols = [], []
    for s in signals:
        vdates += [s[0], s[2]]  # s[0] = buy date, s[2] = sell date
        vcols += ["g", "r"]  # green for buy, red for sell
    
    # Generate and save the chart
    fig, _ = mpf.plot(df, type='candle', volume=True, addplot=apds, style='yahoo',
        vlines=dict(vlines=vdates, colors=vcols, linewidths=1, linestyle='--'),
        title=f"{ticker} {year} Signals", returnfig=True)
    fig.savefig(f"plots/{ticker}_{year}.png"); plt.close(fig)

# ============================================================
# FUNCTION: backtest_year
# PURPOSE: Runs the trading strategy for a single year across all stocks
# PROCESS:
#   1. Scan all CSV files in YahooStockData folder
#   2. For each stock, calculate Bollinger Bands and find buy/sell signals
#   3. Sort all potential trades by date (chronologically)
#   4. Execute trades sequentially using full capital (compounds gains)
#   5. Save results to CSV and generate charts for executed trades
# OUTPUT: Compound return % for the year
# ============================================================
def backtest_year(year):
    all_signals = []
    df_map = {}

    # STEP 1: Collect signals from all tickers for the given year
    for csv in glob.glob("YahooStockData/*.csv"):
        ticker = os.path.basename(csv).replace(".csv", "")
        df = pd.read_csv(csv)
        df["Date"] = pd.to_datetime(df["Date"])
        df.set_index("Date", inplace=True)
        df = df[df.index.year == year]  # Filter to only this year's data
        if len(df) < period:
            continue  # Skip if not enough data for moving average
        df = calculate_bands(df).dropna()  # Calculate indicators
        signals = find_signals(df)  # Find buy/sell opportunities
        if not signals:
            continue
        df_map[ticker] = df  # Store dataframe for later charting
        
        # Convert signals to list format with profit calculations
        for s in signals:
            pct = (s[3] - s[1]) / s[1] * 100
            # store as list: ticker, buy_date, buy_price, sell_date, sell_price, profit_pct, %Below_Lower, days_held
            all_signals.append([ticker, s[0], s[1], s[2], s[3], pct, s[4], s[5]])

    # STEP 2: If no signals across all tickers, return 0
    if not all_signals:
        return 0

    # STEP 3: Sort by buy date, and prefer higher profit on the same buy date
    all_signals.sort(key=lambda x: (x[1], -x[5]))

    # STEP 4: Execute trades sequentially with compounding capital
    capital = initial_capital
    executed_trades = []
    # Track next available date to prevent overlapping positions
    next_available_date = pd.Timestamp(year=year, month=1, day=1)

    for sig in all_signals:
        ticker, buy_date, buy_price, sell_date, sell_price, pct, below, days_held = sig
        # Only take the trade if its buy date is on/after the next available date
        if buy_date >= next_available_date:
            # Execute trade with full capital (all-in strategy)
            shares = capital / buy_price
            capital = shares * sell_price  # Capital compounds with each trade
            executed_trades.append([ticker, buy_date, buy_price, sell_date, sell_price, pct, below, days_held])
            # Update next available date: can buy on the sell day or later
            next_available_date = sell_date
            
            # Generate chart for executed trade
            try:
                df = df_map.get(ticker)
                if df is not None:
                    # recreate the original signal tuple format for plotting
                    plot_signals = [(buy_date, buy_price, sell_date, sell_price, below, days_held)]
                    plot_chart(df, plot_signals, ticker, year)
            except Exception:
                pass  # Skip plotting if errors occur

    # STEP 5: Save executed trades for the year to CSV
    if executed_trades:
        pd.DataFrame(executed_trades, columns=["Ticker","Buy_Date","Buy_Price","Sell_Date","Sell_Price",
                                                "Profit%","%Below_Lower","Days_Held"]).to_csv(f"{year}_perf.csv", index=False)

    # Calculate compound return for the year based on sequential single-asset execution
    compound_return = (capital - initial_capital) / initial_capital * 100
    return compound_return

# ============================================================
# FUNCTION: multi_year_backtest
# PURPOSE: Main function that runs the backtest across all years (2014-2025)
# PROCESS:
#   1. Runs backtest_year() for each year
#   2. Compounds the returns across years multiplicatively
#   3. Saves summary results to results.txt
#   4. Prints final compound growth factor
# ============================================================
def multi_year_backtest():
    os.makedirs("plots", exist_ok=True)
    with open("results.txt", "w", encoding='utf-8') as f:
        f.write("Strategy Description:\n" + strategy_description + "\n\n")
        f.write("GPT Prompt:\nCreate a stock trading strategy using Bollinger Bands with compound returns tracking\n\n")
        f.write("Multi-Year Backtest Results (2014–2025)\n" + "="*50 + "\n")

        comp_factor = 1  # Tracks cumulative compound growth
        for year in years_to_test[::-1]:  # Reverse order for reporting (2025 -> 2014)
            gain = backtest_year(year)  # Run backtest for this year
            comp_factor *= (1 + gain / 100)  # Compound the returns
            f.write(f"Finished processing year {year}. Compounded gain: {gain:.2f}%\n")
        f.write("\nFinal Compounded Return (2014–2025): {:.3f}x\n".format(comp_factor))
        print(f"\n12-Year Compound Growth: {comp_factor:.3f}x\nResults saved to results.txt")

# ============================================================
# SCRIPT ENTRY POINT
# Runs the multi-year backtest when script is executed directly
# ============================================================
if __name__ == "__main__":
    multi_year_backtest()
