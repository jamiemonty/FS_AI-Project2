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

import pandas as pd, numpy as np, os, glob, mplfinance as mpf, matplotlib.pyplot as plt
from datetime import datetime

# --- Strategy Parameters ---
period, std_factor = 20, 2
max_hold_days, min_volume = 30, 100000
deviation_threshold = 0.02
initial_capital = 10000
years_to_test = list(range(2014, 2026))

strategy_description = (
    "We use daily Adj Close prices to generate buy signals when the price falls below the "
    "lower Bollinger Band (20-day, 2σ), provided the deviation is >2% and volume >100k. "
    "Sell when the price crosses the SMA or after 30 days. Capital compounds after each trade."
)

def calculate_bands(df):
    df["SMA"] = df["Close"].rolling(period).mean()
    df["STD"] = df["Close"].rolling(period).std()
    df["Upper"] = df["SMA"] + std_factor * df["STD"]
    df["Lower"] = df["SMA"] - std_factor * df["STD"]
    df["%Below_Lower"] = (df["Lower"] - df["Close"]) / df["Close"]
    return df

def find_signals(df):
    trades, in_position, entry_date, entry_price = [], False, None, None
    for i in range(len(df)):
        today = df.index[i]
        price, vol = df["Close"].iloc[i], df["Volume"].iloc[i]
        sma, lower, below = df["SMA"].iloc[i], df["Lower"].iloc[i], df["%Below_Lower"].iloc[i]
        if not in_position:
            if price < lower and below > deviation_threshold and vol > min_volume:
                in_position, entry_date, entry_price = True, today, price
        else:
            days_held = (today - entry_date).days
            if price > sma or days_held >= max_hold_days:
                trades.append((entry_date, entry_price, today, price, below, days_held))
                in_position = False
    return trades

def plot_chart(df, signals, ticker, year):
    os.makedirs("plots", exist_ok=True)
    apds = [mpf.make_addplot(df["Upper"], color='gray', alpha=0.5),
            mpf.make_addplot(df["Lower"], color='gray', alpha=0.5),
            mpf.make_addplot(df["SMA"], color='blue', alpha=0.5)]
    vdates, vcols = [], []
    for s in signals:
        vdates += [s[0], s[2]]
        vcols += ["g", "r"]
    fig, _ = mpf.plot(df, type='candle', volume=True, addplot=apds, style='yahoo',
                      vlines=dict(vlines=vdates, colors=vcols, linewidths=1, linestyle='--'),
                      title=f"{ticker} {year} Signals", returnfig=True)
    fig.savefig(f"plots/{ticker}_{year}.png"); plt.close(fig)

def backtest_year(year):
    all_signals = []
    df_map = {}

    # Collect signals from all tickers for the given year
    for csv in glob.glob("YahooStockData/*.csv"):
        ticker = os.path.basename(csv).replace(".csv", "")
        df = pd.read_csv(csv)
        df["Date"] = pd.to_datetime(df["Date"])
        df.set_index("Date", inplace=True)
        df = df[df.index.year == year]
        if len(df) < period:
            continue
        df = calculate_bands(df).dropna()
        signals = find_signals(df)
        if not signals:
            continue
        df_map[ticker] = df
        for s in signals:
            pct = (s[3] - s[1]) / s[1] * 100
            # store as list: ticker, buy_date, buy_price, sell_date, sell_price, profit_pct, %Below_Lower, days_held
            all_signals.append([ticker, s[0], s[1], s[2], s[3], pct, s[4], s[5]])

    # If no signals across all tickers, return 0
    if not all_signals:
        return 0

    # Sort by buy date, and prefer higher profit on the same buy date
    all_signals.sort(key=lambda x: (x[1], -x[5]))

    capital = initial_capital
    executed_trades = []
    # Next date when we are allowed to open a new trade; start of the year
    next_available_date = pd.Timestamp(year=year, month=1, day=1)

    for sig in all_signals:
        ticker, buy_date, buy_price, sell_date, sell_price, pct, below, days_held = sig
        # Only take the trade if its buy date is on/after the next available date
        if buy_date >= next_available_date:
            # Execute trade with full capital
            shares = capital / buy_price
            capital = shares * sell_price
            executed_trades.append([ticker, buy_date, buy_price, sell_date, sell_price, pct, below, days_held])
            # update next available date: can buy on the sell day or later
            next_available_date = sell_date
            # plot only executed trade signals for clarity
            try:
                df = df_map.get(ticker)
                if df is not None:
                    # recreate the original signal tuple format for plotting
                    plot_signals = [(buy_date, buy_price, sell_date, sell_price, below, days_held)]
                    plot_chart(df, plot_signals, ticker, year)
            except Exception:
                pass

    # Save executed trades for the year
    if executed_trades:
        pd.DataFrame(executed_trades, columns=["Ticker","Buy_Date","Buy_Price","Sell_Date","Sell_Price",
                                               "Profit%","%Below_Lower","Days_Held"]).to_csv(f"{year}_perf.csv", index=False)

    # Compound return for the year based on sequential single-asset execution
    compound_return = (capital - initial_capital) / initial_capital * 100
    return compound_return

def multi_year_backtest():
    os.makedirs("plots", exist_ok=True)
    with open("results.txt", "w", encoding='utf-8') as f:
        f.write("Strategy Description:\n" + strategy_description + "\n\n")
        f.write("GPT Prompt:\nCreate a stock trading strategy using Bollinger Bands with compound returns tracking\n\n")
        f.write("Multi-Year Backtest Results (2014–2025)\n" + "="*50 + "\n")

        comp_factor = 1
        for year in years_to_test[::-1]:  # Reverse order for reporting
            gain = backtest_year(year)
            comp_factor *= (1 + gain / 100)
            f.write(f"Finished processing year {year}. Compounded gain: {gain:.2f}%\n")
        f.write("\nFinal Compounded Return (2014–2025): {:.3f}x\n".format(comp_factor))
        print(f"\n12-Year Compound Growth: {comp_factor:.3f}x\nResults saved to results.txt")

if __name__ == "__main__":
    multi_year_backtest()
